"""Проверки эталонного набора вопросов.

Ошибка в эталоне не выглядит как ошибка: она превращается в заниженную
метрику и читается как «поиск плохой». Поэтому набор проверяется строже,
чем обычные данные.
"""

import pytest

from ragmdn.config import Settings
from ragmdn.evaluation.golden import (
    GROUPS,
    GoldenSetError,
    group_counts,
    load_golden_set,
    referenced_slugs,
)


@pytest.fixture(scope="module")
def questions():
    return load_golden_set()


def test_set_loads_and_is_not_tiny(questions):
    assert len(questions) >= 40, "набор слишком мал, метрики будут шумными"


def test_all_groups_are_represented(questions):
    counts = group_counts(questions)

    for group in GROUPS:
        assert counts[group] > 0, f"в наборе нет ни одного вопроса группы {group}"


def test_traps_are_a_meaningful_share(questions):
    """Ловушек должно быть достаточно, чтобы доля отказов что-то значила."""
    traps = [q for q in questions if q.is_trap]

    assert len(traps) >= 8, "на нескольких ловушках долю отказов не измерить"


def test_only_traps_have_empty_expectations(questions):
    """Пустой список источников допустим только у ловушек — иначе это опечатка."""
    for question in questions:
        if question.group == "trap":
            assert question.is_trap, f"{question.id}: ловушка не должна иметь источника"
        else:
            assert question.expected_slugs, f"{question.id}: не указан ожидаемый документ"


def test_questions_are_not_empty(questions):
    for question in questions:
        assert question.question.strip(), f"{question.id}: пустой текст вопроса"
        assert len(question.question) > 15, f"{question.id}: подозрительно короткий вопрос"


def test_expected_documents_exist_in_corpus(questions):
    """Главная проверка: каждый ожидаемый документ реально есть на диске.

    Опечатка в идентификаторе документа выглядела бы как «система не нашла
    ответ» — то есть как плохой поиск, а не как ошибка в эталоне.
    """
    settings = Settings(_env_file=None)
    root = settings.raw_dir / "mdn-translated-content" / "files" / "ru"
    if not root.exists():
        pytest.skip("корпус не скачан: python -m ragmdn.corpus.cli")

    missing = []
    for slug in sorted(referenced_slugs(questions)):
        # slug вида Web/JavaScript/Reference/... соответствует пути в нижнем регистре
        path = root / slug.lower() / "index.md"
        if not path.exists():
            missing.append(slug)

    assert not missing, f"эталон ссылается на несуществующие документы: {missing}"


def test_natural_questions_avoid_exact_method_names(questions):
    """Вопросы группы natural должны быть «своими словами».

    Если в них уже названы точные термины, группа перестаёт отличаться
    от direct, и сравнение способов поиска теряет смысл.
    """
    forbidden = ("filter(", "map(", "reduce(", "forEach(", "justify-content", "Cache-Control")

    for question in questions:
        if question.group != "natural":
            continue
        lowered = question.question.lower()
        for term in forbidden:
            assert term.lower() not in lowered, (
                f"{question.id}: в «человеческом» вопросе назван точный термин {term!r}"
            )


def test_rejects_unknown_group(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "version: 1\nquestions:\n"
        "  - id: x1\n    group: телепатия\n    question: вопрос\n",
        encoding="utf-8",
    )

    with pytest.raises(GoldenSetError, match="неизвестная группа"):
        load_golden_set(bad)


def test_rejects_duplicate_ids(tmp_path):
    bad = tmp_path / "dup.yaml"
    bad.write_text(
        "version: 1\nquestions:\n"
        "  - id: x1\n    group: direct\n    question: первый\n    expected_slugs: [A]\n"
        "  - id: x1\n    group: direct\n    question: второй\n    expected_slugs: [B]\n",
        encoding="utf-8",
    )

    with pytest.raises(GoldenSetError, match="повторяющиеся"):
        load_golden_set(bad)
