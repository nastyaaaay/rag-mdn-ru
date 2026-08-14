"""Модель-судья: проверка обоснованности ответов.

Судья получает вопрос, ответ системы и те же фрагменты, по которым ответ
составлялся, и решает, подтверждается ли сказанное этими фрагментами.

**Судья тоже может ошибаться, и это не оговорка для приличия.** Роль судьи
играет та же семимиллиардная модель, что и отвечает, — ждать от неё
безупречных суждений нет оснований. Поэтому:

* вердикт ограничен тремя словами, а не свободным текстом: свободный ответ
  слабая модель превращает в рассуждение, из которого нельзя извлечь оценку;
* согласие судьи с ручной разметкой измеряется отдельно
  (`run_judge.py --agreement`), и все его цифры читаются с этой поправкой.

Без такой проверки «обоснованность 85%» — число, взятое у модели на слово,
а весь смысл проекта в том, чтобы на слово ничего не брать.
"""

import re
from dataclasses import dataclass
from enum import Enum

from ragmdn.evaluation.generation import AnswerRecord
from ragmdn.llm import ChatModel, Message


class Verdict(str, Enum):
    """Вердикт судьи об обоснованности ответа."""

    GROUNDED = "подтверждается"
    PARTIAL = "частично"
    UNGROUNDED = "не_подтверждается"
    UNPARSABLE = "не_разобрано"

    @property
    def score(self) -> float:
        """Числовая оценка для усреднения."""
        return {
            Verdict.GROUNDED: 1.0,
            Verdict.PARTIAL: 0.5,
            Verdict.UNGROUNDED: 0.0,
            Verdict.UNPARSABLE: 0.0,
        }[self]


JUDGE_PROMPT = """\
Ты проверяешь, подтверждается ли ответ приведёнными фрагментами документации.

Твоя задача — НЕ оценивать, правильный ли ответ по существу, и НЕ полагаться
на собственные знания. Проверяй ровно одно: следует ли сказанное в ответе
из приведённых фрагментов.

Ответь ОДНИМ словом, без пояснений:

ПОДТВЕРЖДАЕТСЯ — всё сказанное следует из фрагментов
ЧАСТИЧНО — часть следует, часть добавлена от себя
НЕ_ПОДТВЕРЖДАЕТСЯ — сказанное из фрагментов не следует

Никакого другого текста в ответе быть не должно.
"""

JUDGE_TEMPLATE = """\
Фрагменты документации:

{context}

Вопрос пользователя: {question}

Ответ системы: {answer}

Одно слово:"""

_VERDICT_PATTERNS = (
    (re.compile(r"НЕ[_\s]?ПОДТВЕРЖДА", re.IGNORECASE), Verdict.UNGROUNDED),
    (re.compile(r"ЧАСТИЧНО", re.IGNORECASE), Verdict.PARTIAL),
    (re.compile(r"ПОДТВЕРЖДА", re.IGNORECASE), Verdict.GROUNDED),
)


def parse_verdict(text: str) -> Verdict:
    """Достаёт вердикт из ответа судьи.

    Порядок проверки важен: «НЕ_ПОДТВЕРЖДАЕТСЯ» содержит в себе
    «ПОДТВЕРЖДА», и при обратном порядке отрицание превратилось бы
    в свою противоположность — самая обидная из возможных ошибок здесь.
    """
    for pattern, verdict in _VERDICT_PATTERNS:
        if pattern.search(text):
            return verdict
    return Verdict.UNPARSABLE


def build_judge_messages(record: AnswerRecord) -> list[Message]:
    context = "\n\n".join(
        f"[{number}] {text}" for number, text in enumerate(record.context, start=1)
    )
    return [
        Message(role="system", content=JUDGE_PROMPT),
        Message(
            role="user",
            content=JUDGE_TEMPLATE.format(
                context=context, question=record.question, answer=record.answer
            ),
        ),
    ]


@dataclass(frozen=True)
class Judgement:
    question_id: str
    verdict: Verdict
    raw: str


def judge_answer(model: ChatModel, record: AnswerRecord) -> Judgement:
    """Оценивает обоснованность одного ответа.

    Отказы судье не показываются: фраза «в документах ответа нет» ничего
    не утверждает о предметной области, проверять в ней нечего. Считать её
    необоснованной было бы прямой ошибкой — это правильное поведение.
    """
    if record.is_refusal:
        return Judgement(record.question_id, Verdict.GROUNDED, "отказ не оценивается")

    raw = model.complete(build_judge_messages(record)).strip()
    return Judgement(record.question_id, parse_verdict(raw), raw)


def groundedness(judgements: list[Judgement]) -> float:
    """Средняя обоснованность: 1 за подтверждённый ответ, 0.5 за частичный."""
    if not judgements:
        return 0.0
    return sum(j.verdict.score for j in judgements) / len(judgements)


def agreement_rate(
    judgements: list[Judgement], manual: dict[str, Verdict]
) -> tuple[float, list[str]]:
    """Насколько судья согласен с ручной разметкой.

    Возвращает долю совпадений и список расхождений. Это число —
    поправочный коэффициент ко всем остальным оценкам судьи: если он
    совпадает с человеком в 70% случаев, «обоснованность 85%» надо
    читать именно с этой оговоркой.
    """
    common = [j for j in judgements if j.question_id in manual]
    if not common:
        return 0.0, []

    disagreements = [
        f"{j.question_id}: судья «{j.verdict.value}», человек «{manual[j.question_id].value}»"
        for j in common
        if j.verdict != manual[j.question_id]
    ]
    return (len(common) - len(disagreements)) / len(common), disagreements
