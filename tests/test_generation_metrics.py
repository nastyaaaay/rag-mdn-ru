"""Тесты метрик качества ответов.

Метрики этой группы считаются без модели, поэтому проверяются точно —
на записях, составленных вручную.
"""

import pytest

from ragmdn.evaluation.generation import (
    AnswerRecord,
    compute_metrics,
    load_records,
    save_records,
)


def record(
    *,
    qid: str = "q1",
    group: str = "direct",
    refusal: bool = False,
    invalid_citation: bool = False,
    retrieved: tuple[str, ...] = ("A",),
    cited: tuple[str, ...] = ("A",),
    expected: tuple[str, ...] = ("A",),
    trap: bool = False,
) -> AnswerRecord:
    return AnswerRecord(
        question_id=qid,
        group=group,
        question="вопрос",
        answer="ответ",
        is_refusal=refusal,
        has_invalid_citation=invalid_citation,
        cited=(1,),
        retrieved_slugs=retrieved,
        cited_slugs=cited,
        expected_slugs=expected,
        is_trap=trap,
    )


def test_refusal_rate_on_traps_counts_only_traps():
    """Главная метрика честности считается только по ловушкам."""
    records = [
        record(qid="t1", group="trap", trap=True, refusal=True, expected=()),
        record(qid="t2", group="trap", trap=True, refusal=True, expected=()),
        record(qid="t3", group="trap", trap=True, refusal=False, expected=()),
        record(qid="d1"),  # обычный вопрос не должен влиять
    ]

    metrics = compute_metrics(records)

    assert metrics.traps == 3
    assert metrics.correct_refusals == 2
    assert metrics.refusal_rate_on_traps == pytest.approx(2 / 3)


def test_false_refusal_counts_only_answerable():
    """Отказ там, где ответ был, — отдельная ошибка, противоположная выдумке."""
    records = [
        record(qid="d1", refusal=True),
        record(qid="d2", refusal=False),
        record(qid="t1", group="trap", trap=True, refusal=True, expected=()),
    ]

    metrics = compute_metrics(records)

    assert metrics.answerable == 2
    assert metrics.false_refusals == 1
    assert metrics.false_refusal_rate == pytest.approx(0.5)


def test_invalid_citation_rate_covers_all_answers():
    records = [
        record(qid="d1", invalid_citation=True),
        record(qid="d2", invalid_citation=False),
        record(qid="t1", group="trap", trap=True, invalid_citation=True, expected=()),
    ]

    metrics = compute_metrics(records)

    assert metrics.invalid_citations == 2
    assert metrics.invalid_citation_rate == pytest.approx(2 / 3)


def test_citation_precision_ignores_cases_where_search_failed():
    """Если поиск не нашёл нужный документ, модель не могла на него сослаться.

    Такие случаи не должны портить метрику цитирования — это промах поиска,
    а не выдумка модели.
    """
    records = [
        # поиск нашёл нужное, модель сослалась верно
        record(qid="d1", retrieved=("A", "B"), cited=("A",), expected=("A",)),
        # поиск нашёл нужное, но модель сослалась на чужое
        record(qid="d2", retrieved=("A", "B"), cited=("B",), expected=("A",)),
        # поиск не нашёл нужное — случай не учитывается вовсе
        record(qid="d3", retrieved=("X", "Y"), cited=("X",), expected=("A",)),
    ]

    metrics = compute_metrics(records)

    assert metrics.context_had_answer == 2
    assert metrics.cited_expected == 1
    assert metrics.citation_precision == pytest.approx(0.5)


def test_expected_document_was_retrieved_flag():
    assert record(retrieved=("A", "B"), expected=("B",)).expected_document_was_retrieved
    assert not record(retrieved=("X",), expected=("A",)).expected_document_was_retrieved


def test_metrics_by_group_are_separate():
    records = [
        record(qid="d1", group="direct", refusal=False),
        record(qid="n1", group="natural", refusal=True),
        record(qid="n2", group="natural", refusal=True),
    ]

    metrics = compute_metrics(records)

    assert metrics.by_group["direct"]["refusals"] == 0
    assert metrics.by_group["natural"]["refusals"] == 2
    assert metrics.by_group["natural"]["total"] == 2


def test_empty_input_does_not_divide_by_zero():
    metrics = compute_metrics([])

    assert metrics.refusal_rate_on_traps == 0.0
    assert metrics.false_refusal_rate == 0.0
    assert metrics.invalid_citation_rate == 0.0
    assert metrics.citation_precision == 0.0


def test_records_survive_saving_and_loading(tmp_path):
    """Генерация занимает десятки минут — результат обязан переживать запись."""
    original = [record(qid="d1"), record(qid="t1", group="trap", trap=True, expected=())]
    path = tmp_path / "records.json"

    save_records(original, path)
    restored = load_records(path)

    assert restored == original
