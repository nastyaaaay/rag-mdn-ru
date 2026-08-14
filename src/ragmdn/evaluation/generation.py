"""Измерение качества ответов.

Метрики намеренно разделены на две группы, потому что доверие к ним разное.

**Без модели-судьи** — считаются кодом, воспроизводимы точно, спорить с ними
нельзя:

* доля корректных отказов на ловушках — главная метрика честности;
* доля ложных отказов: система сдалась там, где ответ в документах был;
* доля выдуманных ссылок: модель сослалась на фрагмент, которого ей
  не передавали. Номер вне диапазона взяться неоткуда, кроме как из головы.

**С моделью-судьёй** — обоснованность и полнота. Судья сам может ошибаться,
поэтому его согласие с человеком измеряется отдельно (`judge.py`), и все
цифры этой группы читаются с той поправкой.

Результаты прогона сохраняются в файл: генерация 52 ответов занимает
десятки минут, и гонять её заново ради каждой новой метрики бессмысленно.
"""

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ragmdn.answer import Answer
from ragmdn.evaluation.golden import Question


@dataclass(frozen=True)
class AnswerRecord:
    """Ответ на один эталонный вопрос со всем, что нужно для оценки."""

    question_id: str
    group: str
    question: str
    answer: str
    is_refusal: bool
    has_invalid_citation: bool
    cited: tuple[int, ...]
    #: Документы, которые поиск передал модели, в порядке выдачи.
    retrieved_slugs: tuple[str, ...]
    #: Документы, на которые модель реально сослалась.
    cited_slugs: tuple[str, ...]
    expected_slugs: tuple[str, ...]
    is_trap: bool
    #: Тексты фрагментов — нужны судье, чтобы проверять по ним обоснованность.
    context: tuple[str, ...] = ()

    @property
    def expected_document_was_retrieved(self) -> bool:
        """Нужный документ вообще попал в контекст?

        Без этого нельзя честно трактовать плохой ответ: если поиск не нашёл
        документ, модель не могла ответить верно, и вина не на ней.
        """
        return any(slug in self.expected_slugs for slug in self.retrieved_slugs)


def make_record(question: Question, answer: Answer) -> AnswerRecord:
    return AnswerRecord(
        question_id=question.id,
        group=question.group,
        question=question.question,
        answer=answer.text,
        is_refusal=answer.is_refusal,
        has_invalid_citation=answer.has_invalid_citation,
        cited=answer.cited,
        retrieved_slugs=tuple(hit.slug for hit in answer.hits),
        cited_slugs=tuple(dict.fromkeys(hit.slug for hit in answer.sources)),
        expected_slugs=question.expected_slugs,
        is_trap=question.is_trap,
        context=tuple(hit.content for hit in answer.hits),
    )


@dataclass
class GenerationMetrics:
    """Метрики, посчитанные без участия модели-судьи."""

    total: int = 0
    traps: int = 0
    answerable: int = 0

    #: Ловушки, на которых система корректно призналась в незнании.
    correct_refusals: int = 0
    #: Отвечаемые вопросы, на которых система сдалась зря.
    false_refusals: int = 0
    #: Ответы со ссылкой на несуществующий фрагмент.
    invalid_citations: int = 0
    #: Ответы, где нужный документ был в контексте.
    context_had_answer: int = 0
    #: Из них — те, где модель сослалась именно на нужный документ.
    cited_expected: int = 0

    by_group: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def refusal_rate_on_traps(self) -> float:
        """Главная метрика честности: доля признаний «не знаю» на ловушках."""
        return self.correct_refusals / self.traps if self.traps else 0.0

    @property
    def false_refusal_rate(self) -> float:
        return self.false_refusals / self.answerable if self.answerable else 0.0

    @property
    def invalid_citation_rate(self) -> float:
        return self.invalid_citations / self.total if self.total else 0.0

    @property
    def citation_precision(self) -> float:
        """Из случаев, когда нужный документ был в контексте, — как часто
        модель сослалась именно на него."""
        return self.cited_expected / self.context_had_answer if self.context_had_answer else 0.0


def compute_metrics(records: Sequence[AnswerRecord]) -> GenerationMetrics:
    metrics = GenerationMetrics(total=len(records))

    for record in records:
        group = metrics.by_group.setdefault(
            record.group, {"total": 0, "refusals": 0, "invalid_citations": 0}
        )
        group["total"] += 1
        if record.is_refusal:
            group["refusals"] += 1
        if record.has_invalid_citation:
            group["invalid_citations"] += 1
            metrics.invalid_citations += 1

        if record.is_trap:
            metrics.traps += 1
            if record.is_refusal:
                metrics.correct_refusals += 1
            continue

        metrics.answerable += 1
        if record.is_refusal:
            metrics.false_refusals += 1

        if record.expected_document_was_retrieved:
            metrics.context_had_answer += 1
            if any(slug in record.expected_slugs for slug in record.cited_slugs):
                metrics.cited_expected += 1

    return metrics


def save_records(records: Sequence[AnswerRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_records(path: Path) -> list[AnswerRecord]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        AnswerRecord(
            **{
                **entry,
                "cited": tuple(entry["cited"]),
                "retrieved_slugs": tuple(entry["retrieved_slugs"]),
                "cited_slugs": tuple(entry["cited_slugs"]),
                "expected_slugs": tuple(entry["expected_slugs"]),
                "context": tuple(entry.get("context", ())),
            }
        )
        for entry in data
    ]
