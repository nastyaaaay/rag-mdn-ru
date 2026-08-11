"""Тесты метрик качества поиска.

Метрика — инструмент измерения, и если врёт она, врёт весь отчёт. Поэтому
проверяется на данных с заранее известным ответом, посчитанным вручную.
"""

import pytest

from ragmdn.evaluation.golden import Question
from ragmdn.evaluation.retrieval import (
    aggregate,
    evaluate_question,
    first_relevant_rank,
)
from ragmdn.search import SearchHit


def hit(slug: str) -> SearchHit:
    return SearchHit(
        chunk_id=0,
        slug=slug,
        title="Заголовок",
        source_url=f"https://developer.mozilla.org/ru/docs/{slug}",
        heading_path="Путь",
        content="Текст",
        score=1.0,
    )


def question(qid: str, group: str, *expected: str) -> Question:
    return Question(id=qid, group=group, question="достаточно длинный вопрос", expected_slugs=expected)


def test_rank_is_one_based():
    """Первая позиция — 1, а не 0: иначе MRR получится больше единицы."""
    assert first_relevant_rank([hit("A")], ["A"]) == 1


def test_rank_finds_first_match_not_any():
    assert first_relevant_rank([hit("X"), hit("A"), hit("A")], ["A"]) == 2


def test_rank_is_none_when_absent():
    assert first_relevant_rank([hit("X"), hit("Y")], ["A"]) is None


def test_any_of_several_expected_documents_counts():
    """Если ответ есть в нескольких документах, годится любой из них."""
    assert first_relevant_rank([hit("B")], ["A", "B"]) == 1


def test_reciprocal_rank_values():
    outcome = evaluate_question(question("q1", "direct", "A"), [hit("X"), hit("A")])

    assert outcome.rank == 2
    assert outcome.reciprocal_rank == pytest.approx(0.5)


def test_missed_question_contributes_zero_to_mrr():
    outcome = evaluate_question(question("q1", "direct", "A"), [hit("X")])

    assert outcome.rank is None
    assert outcome.reciprocal_rank == 0.0


def test_recall_at_k_counts_only_within_k():
    outcomes = [
        evaluate_question(question("q1", "direct", "A"), [hit("A")]),           # ранг 1
        evaluate_question(question("q2", "direct", "B"), [hit("X"), hit("B")]),  # ранг 2
        evaluate_question(question("q3", "direct", "C"), [hit("X")]),            # не найден
    ]

    metrics = aggregate(outcomes)["direct"]

    assert metrics.total == 3
    assert metrics.recall[1] == pytest.approx(1 / 3)
    assert metrics.recall[3] == pytest.approx(2 / 3)
    assert metrics.misses == ["q3"]


def test_mrr_is_averaged_over_all_questions_including_misses():
    """Промах не выбрасывается из среднего, иначе метрика льстит системе."""
    outcomes = [
        evaluate_question(question("q1", "direct", "A"), [hit("A")]),   # 1.0
        evaluate_question(question("q2", "direct", "B"), [hit("X")]),   # 0.0
    ]

    metrics = aggregate(outcomes)["direct"]

    assert metrics.mrr == pytest.approx(0.5)


def test_traps_are_excluded_from_recall():
    """У ловушки нет верного документа: включать её в Recall бессмысленно.

    Иначе каждая ловушка засчитывалась бы как промах и занижала метрику,
    хотя правильное поведение системы на ней — как раз ничего не найти.
    """
    outcomes = [
        evaluate_question(question("q1", "direct", "A"), [hit("A")]),
        evaluate_question(question("t1", "trap"), [hit("X")]),
    ]

    metrics = aggregate(outcomes)

    assert "trap" not in metrics
    assert metrics["ВСЕГО"].total == 1
    assert metrics["ВСЕГО"].recall[1] == 1.0


def test_groups_are_reported_separately():
    """Разбивка по группам обязательна: среднее скрывает слабые места."""
    outcomes = [
        evaluate_question(question("d1", "direct", "A"), [hit("A")]),
        evaluate_question(question("n1", "natural", "B"), [hit("X")]),
    ]

    metrics = aggregate(outcomes)

    assert metrics["direct"].recall[1] == 1.0
    assert metrics["natural"].recall[1] == 0.0
    assert metrics["ВСЕГО"].recall[1] == pytest.approx(0.5)


def test_empty_input_does_not_crash():
    assert aggregate([]) == {}
