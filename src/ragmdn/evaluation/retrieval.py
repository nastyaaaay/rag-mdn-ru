"""Метрики качества поиска.

Считаются **без языковой модели** — только сопоставление найденных документов
с эталоном. Поэтому цифры детерминированы: один и тот же индекс и один и тот
же набор вопросов всегда дают один и тот же результат. Это фундамент отчёта:
всё, что меряется с участием модели-судьи (шаг 11), нуждается в оговорках,
а эти числа — нет.

Что считаем:

* **Recall@k** — в какой доле вопросов нужный документ попал в первые k
  результатов. Отвечает на вопрос «дошло ли до пользователя вообще».
* **MRR** (mean reciprocal rank) — насколько высоко он оказался. Если нужный
  документ стабильно на первом месте, MRR равен 1; если на пятом — 0.2.
  Recall этого не показывает: попадание на первом и на десятом месте для
  него одинаково.

Обе метрики считаются **по группам вопросов отдельно**. Среднее по всему
набору скрывает именно то, что интересно: система может отлично отвечать на
прямые вопросы и проваливать бытовые формулировки, а в среднем выглядеть
прилично.

Ловушки (вопросы без верного ответа) в этих метриках не участвуют: искать
там нечего. Для них считается своя величина — доля случаев, когда система
удержалась и не выдала ничего похожего на уверенный ответ; она появится
на шаге 11 вместе с генерацией.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from ragmdn.evaluation.golden import Question
from ragmdn.search import SearchHit

#: Значения k, для которых считается Recall.
RECALL_AT = (1, 3, 5, 10)


@dataclass(frozen=True)
class QuestionOutcome:
    """Результат одного вопроса."""

    question: Question
    found_slugs: tuple[str, ...]
    #: Позиция первого верного документа, начиная с 1. None — не найден.
    rank: int | None

    @property
    def reciprocal_rank(self) -> float:
        return 0.0 if self.rank is None else 1 / self.rank


@dataclass
class GroupMetrics:
    """Метрики по одной группе вопросов."""

    group: str
    total: int = 0
    recall: dict[int, float] = field(default_factory=dict)
    mrr: float = 0.0
    #: Вопросы, где верный документ не нашёлся вообще — самое интересное
    #: для разбора: именно они показывают, где система слепа.
    misses: list[str] = field(default_factory=list)


def first_relevant_rank(hits: Sequence[SearchHit], expected: Sequence[str]) -> int | None:
    """Позиция первого фрагмента из подходящего документа (начиная с 1).

    Сравниваются документы, а не фрагменты: вопрос задан документу, и
    неважно, какая именно его часть нашлась.
    """
    expected_set = set(expected)
    for position, hit in enumerate(hits, start=1):
        if hit.slug in expected_set:
            return position
    return None


def evaluate_question(question: Question, hits: Sequence[SearchHit]) -> QuestionOutcome:
    return QuestionOutcome(
        question=question,
        found_slugs=tuple(hit.slug for hit in hits),
        rank=first_relevant_rank(hits, question.expected_slugs),
    )


def aggregate(outcomes: Sequence[QuestionOutcome]) -> dict[str, GroupMetrics]:
    """Сводит результаты по группам вопросов.

    Ловушки исключаются: у них нет верного документа, и Recall для них
    бессмыслен. Их проверка — отдельная метрика на шаге 11.
    """
    scored = [outcome for outcome in outcomes if not outcome.question.is_trap]

    by_group: dict[str, list[QuestionOutcome]] = {}
    for outcome in scored:
        by_group.setdefault(outcome.question.group, []).append(outcome)

    metrics: dict[str, GroupMetrics] = {}
    for group, group_outcomes in sorted(by_group.items()):
        metrics[group] = _metrics_for(group, group_outcomes)

    if scored:
        metrics["ВСЕГО"] = _metrics_for("ВСЕГО", scored)

    return metrics


def _metrics_for(group: str, outcomes: Sequence[QuestionOutcome]) -> GroupMetrics:
    total = len(outcomes)
    result = GroupMetrics(group=group, total=total)

    for k in RECALL_AT:
        found = sum(1 for o in outcomes if o.rank is not None and o.rank <= k)
        result.recall[k] = found / total if total else 0.0

    result.mrr = sum(o.reciprocal_rank for o in outcomes) / total if total else 0.0
    result.misses = [o.question.id for o in outcomes if o.rank is None]
    return result


def render_markdown(
    metrics_by_method: dict[str, dict[str, GroupMetrics]],
    outcomes_by_method: dict[str, list[QuestionOutcome]],
) -> str:
    """Отчёт о качестве поиска в виде таблиц."""
    lines: list[str] = ["# Качество поиска", ""]
    lines.append(
        "Метрики посчитаны без участия языковой модели: сопоставляются только "
        "найденные документы с эталонными. Цифры воспроизводимы — один и тот же "
        "индекс всегда даёт один и тот же результат."
    )
    lines.append("")
    lines.append(
        "**Recall@k** — доля вопросов, где нужный документ попал в первые k "
        "результатов. **MRR** — насколько высоко он оказался (1.0 значит "
        "«всегда первым»)."
    )
    lines.append("")

    for method, metrics in metrics_by_method.items():
        lines.append(f"## Способ поиска: `{method}`")
        lines.append("")
        lines.append("| Группа вопросов | Вопросов | R@1 | R@3 | R@5 | R@10 | MRR |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for group, m in metrics.items():
            recalls = " | ".join(f"{m.recall[k]:.0%}" for k in RECALL_AT)
            lines.append(f"| {group} | {m.total} | {recalls} | {m.mrr:.3f} |")
        lines.append("")

        misses = metrics.get("ВСЕГО", GroupMetrics("")).misses
        if misses:
            lines.append(f"Не найдено вовсе: {len(misses)} вопросов — `{'`, `'.join(misses)}`")
            lines.append("")

    # Разбор промахов: без него таблица говорит «плохо», но не говорит «почему».
    lines.append("## Вопросы, на которых система промахнулась")
    lines.append("")
    any_miss = False
    for method, outcomes in outcomes_by_method.items():
        missed = [o for o in outcomes if not o.question.is_trap and o.rank is None]
        if not missed:
            continue
        any_miss = True
        lines.append(f"### `{method}`")
        lines.append("")
        for outcome in missed:
            lines.append(f"**{outcome.question.id}** ({outcome.question.group}): "
                         f"{outcome.question.question}")
            lines.append("")
            lines.append(f"- ожидалось: `{'`, `'.join(outcome.question.expected_slugs)}`")
            found = ", ".join(f"`{slug}`" for slug in dict.fromkeys(outcome.found_slugs))
            lines.append(f"- найдено: {found or '—'}")
            lines.append("")
    if not any_miss:
        lines.append("Промахов нет.")
        lines.append("")

    return "\n".join(lines)
