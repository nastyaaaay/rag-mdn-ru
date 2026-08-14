"""Тесты модели-судьи.

Сама модель здесь не вызывается: проверяется разбор вердикта, промпт
и арифметика согласия с разметкой.
"""

import pytest

from ragmdn.evaluation.generation import AnswerRecord
from ragmdn.evaluation.judge import (
    Judgement,
    Verdict,
    agreement_rate,
    build_judge_messages,
    groundedness,
    judge_answer,
    parse_verdict,
)
from ragmdn.llm import Message


def record(*, qid: str = "q1", refusal: bool = False, answer: str = "ответ") -> AnswerRecord:
    return AnswerRecord(
        question_id=qid,
        group="direct",
        question="вопрос",
        answer=answer,
        is_refusal=refusal,
        has_invalid_citation=False,
        cited=(1,),
        retrieved_slugs=("A",),
        cited_slugs=("A",),
        expected_slugs=("A",),
        is_trap=False,
        context=("текст фрагмента",),
    )


class ScriptedModel:
    def __init__(self, reply: str):
        self.reply = reply
        self.calls = 0

    def complete(self, messages: list[Message]) -> str:
        self.calls += 1
        return self.reply


# --- Разбор вердикта ------------------------------------------------------


def test_negative_verdict_is_not_confused_with_positive():
    """Самая обидная ошибка здесь: «НЕ_ПОДТВЕРЖДАЕТСЯ» содержит внутри
    «ПОДТВЕРЖДА», и при неверном порядке проверки отрицание превратилось бы
    в свою противоположность — метрика честности показывала бы обратное.
    """
    assert parse_verdict("НЕ_ПОДТВЕРЖДАЕТСЯ") is Verdict.UNGROUNDED
    assert parse_verdict("НЕ ПОДТВЕРЖДАЕТСЯ") is Verdict.UNGROUNDED
    assert parse_verdict("ПОДТВЕРЖДАЕТСЯ") is Verdict.GROUNDED


def test_partial_verdict():
    assert parse_verdict("ЧАСТИЧНО") is Verdict.PARTIAL


def test_verdict_is_case_insensitive():
    assert parse_verdict("подтверждается") is Verdict.GROUNDED
    assert parse_verdict("не подтверждается") is Verdict.UNGROUNDED


def test_verdict_survives_extra_chatter():
    """Слабая модель норовит порассуждать вместо одного слова."""
    assert parse_verdict("Мой вердикт: ЧАСТИЧНО, потому что...") is Verdict.PARTIAL


def test_unrecognized_answer_is_marked_unparsable():
    assert parse_verdict("затрудняюсь сказать") is Verdict.UNPARSABLE


def test_unparsable_counts_as_zero_not_as_success():
    """Неразобранный вердикт нельзя засчитывать как успех — только строго."""
    assert Verdict.UNPARSABLE.score == 0.0


# --- Оценка ---------------------------------------------------------------


def test_refusal_is_not_sent_to_judge():
    """В отказе нечего проверять: он ничего не утверждает о предмете."""
    model = ScriptedModel("НЕ_ПОДТВЕРЖДАЕТСЯ")

    judgement = judge_answer(model, record(refusal=True))

    assert model.calls == 0
    assert judgement.verdict is Verdict.GROUNDED


def test_normal_answer_is_judged():
    model = ScriptedModel("ПОДТВЕРЖДАЕТСЯ")

    judgement = judge_answer(model, record())

    assert model.calls == 1
    assert judgement.verdict is Verdict.GROUNDED


def test_judge_prompt_contains_answer_and_context():
    messages = build_judge_messages(record(answer="Метод создаёт массив [1]."))
    user = messages[1].content

    assert "Метод создаёт массив [1]." in user
    assert "текст фрагмента" in user


def test_judge_prompt_forbids_using_own_knowledge():
    system = build_judge_messages(record())[0].content

    assert "НЕ полагаться" in system or "не полагайся" in system.lower()


def test_groundedness_averages_verdicts():
    judgements = [
        Judgement("a", Verdict.GROUNDED, ""),
        Judgement("b", Verdict.PARTIAL, ""),
        Judgement("c", Verdict.UNGROUNDED, ""),
    ]

    assert groundedness(judgements) == pytest.approx((1.0 + 0.5 + 0.0) / 3)


def test_groundedness_of_nothing_is_zero():
    assert groundedness([]) == 0.0


# --- Согласие с разметкой -------------------------------------------------


def test_agreement_counts_only_labelled_answers():
    judgements = [
        Judgement("a", Verdict.GROUNDED, ""),
        Judgement("b", Verdict.UNGROUNDED, ""),
        Judgement("c", Verdict.PARTIAL, ""),  # не размечен
    ]
    manual = {"a": Verdict.GROUNDED, "b": Verdict.GROUNDED}

    rate, disagreements = agreement_rate(judgements, manual)

    assert rate == pytest.approx(0.5)
    assert len(disagreements) == 1
    assert "b" in disagreements[0]


def test_full_agreement():
    judgements = [Judgement("a", Verdict.GROUNDED, "")]
    manual = {"a": Verdict.GROUNDED}

    rate, disagreements = agreement_rate(judgements, manual)

    assert rate == 1.0
    assert disagreements == []


def test_agreement_without_labels_is_zero_not_one():
    """Отсутствие разметки — это «не измерено», а не «идеальное согласие»."""
    rate, disagreements = agreement_rate([Judgement("a", Verdict.GROUNDED, "")], {})

    assert rate == 0.0
    assert disagreements == []
