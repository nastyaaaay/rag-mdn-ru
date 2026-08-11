"""Эталонный набор вопросов: загрузка и проверка.

Набор — самая хрупкая часть измерения. Ошибка в нём не проявляется сбоем:
если вопрос ссылается на документ, которого нет в корпусе, метрика просто
покажет, что система его «не нашла», и выглядеть это будет как проблема
поиска, а не как опечатка в эталоне. Поэтому набор проверяется отдельно
и придирчиво.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import yaml

from ragmdn.config import PROJECT_ROOT

GOLDEN_SET_PATH = PROJECT_ROOT / "eval" / "golden_set.yaml"

#: Группы вопросов. Метрики считаются по каждой отдельно: усреднение по
#: всему набору скрыло бы именно то, что интереснее всего.
GROUPS = ("direct", "natural", "similar", "trap", "cross")


@dataclass(frozen=True)
class Question:
    id: str
    group: str
    question: str
    expected_slugs: tuple[str, ...]
    #: Только для ловушек: слова, которых в корпусе быть не должно.
    #: Проверяются тестом по реальному индексу — ловушка, на которую
    #: в корпусе есть ответ, наказывает систему за правильное поведение.
    absent_terms: tuple[str, ...] = ()

    @property
    def is_trap(self) -> bool:
        """Ловушка: верного документа не существует, ожидается отказ."""
        return not self.expected_slugs


class GoldenSetError(ValueError):
    """Эталонный набор повреждён или противоречив."""


def load_golden_set(path: Path | None = None) -> list[Question]:
    """Читает набор и проверяет его внутреннюю согласованность."""
    path = path or GOLDEN_SET_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict) or "questions" not in raw:
        raise GoldenSetError(f"{path}: ожидался ключ 'questions'")

    questions: list[Question] = []
    for entry in raw["questions"]:
        missing = {"id", "group", "question"} - set(entry)
        if missing:
            raise GoldenSetError(f"в вопросе {entry.get('id', '?')} нет полей: {sorted(missing)}")
        if entry["group"] not in GROUPS:
            raise GoldenSetError(
                f"вопрос {entry['id']}: неизвестная группа {entry['group']!r}, "
                f"допустимы {GROUPS}"
            )
        questions.append(
            Question(
                id=entry["id"],
                group=entry["group"],
                question=entry["question"],
                expected_slugs=tuple(entry.get("expected_slugs") or ()),
                absent_terms=tuple(entry.get("absent_terms") or ()),
            )
        )

    duplicates = [qid for qid, count in Counter(q.id for q in questions).items() if count > 1]
    if duplicates:
        raise GoldenSetError(f"повторяющиеся идентификаторы вопросов: {duplicates}")

    return questions


def group_counts(questions: list[Question]) -> Counter[str]:
    return Counter(q.group for q in questions)


def referenced_slugs(questions: list[Question]) -> set[str]:
    """Все документы, на которые ссылается набор."""
    return {slug for question in questions for slug in question.expected_slugs}
