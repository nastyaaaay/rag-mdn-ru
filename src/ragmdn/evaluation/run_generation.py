"""Прогон эталонного набора через генерацию ответов.

    python -m ragmdn.evaluation.run_generation

Генерирует ответ на каждый вопрос набора и считает метрики, которые
не требуют модели-судьи. Ответы сохраняются в `reports/answers.json`,
чтобы судья (шаг «проверка обоснованности») работал по готовым ответам,
а не гонял генерацию заново — она занимает десятки минут.
"""

import functools
import sys
import time

from ragmdn.answer import answer_question
from ragmdn.config import get_settings
from ragmdn.db import IndexMismatchError, connect
from ragmdn.embeddings import Embedder
from ragmdn.evaluation.generation import (
    AnswerRecord,
    GenerationMetrics,
    compute_metrics,
    make_record,
    save_records,
)
from ragmdn.evaluation.golden import load_golden_set
from ragmdn.llm import LLMError, OpenAICompatibleModel
from ragmdn.search import search

print = functools.partial(print, flush=True)  # noqa: A001

GROUP_TITLES = {
    "direct": "прямые вопросы",
    "natural": "своими словами",
    "similar": "различение похожих",
    "trap": "ловушки",
    "cross": "на стыке тем",
}


def render_report(metrics: GenerationMetrics, records: list[AnswerRecord], settings) -> str:
    lines = ["# Отчёт о качестве ответов", ""]
    lines.append(f"Модель: `{settings.llm_model}`, температура {settings.llm_temperature}.")
    lines.append(f"Вопросов: {metrics.total} (ловушек: {metrics.traps}, "
                 f"с ответом: {metrics.answerable}).")
    lines.append("")
    lines.append("Все метрики этого раздела посчитаны **без участия модели-судьи** —")
    lines.append("только кодом, по тексту ответа. Поэтому они воспроизводимы точно.")
    lines.append("")

    lines.append("## Главные метрики")
    lines.append("")
    lines.append("| Метрика | Значение | Что означает |")
    lines.append("|---|---:|---|")
    lines.append(
        f"| Корректные отказы на ловушках | **{metrics.refusal_rate_on_traps:.0%}** "
        f"({metrics.correct_refusals}/{metrics.traps}) | "
        "система признаёт, что ответа в документах нет |"
    )
    lines.append(
        f"| Ложные отказы | {metrics.false_refusal_rate:.0%} "
        f"({metrics.false_refusals}/{metrics.answerable}) | "
        "сдалась там, где ответ был — противоположная ошибка |"
    )
    lines.append(
        f"| Выдуманные ссылки | {metrics.invalid_citation_rate:.0%} "
        f"({metrics.invalid_citations}/{metrics.total}) | "
        "сослалась на фрагмент, которого не передавали |"
    )
    lines.append(
        f"| Точность цитирования | {metrics.citation_precision:.0%} "
        f"({metrics.cited_expected}/{metrics.context_had_answer}) | "
        "из случаев, где нужный документ был в контексте |"
    )
    lines.append("")

    lines.append("## По группам вопросов")
    lines.append("")
    lines.append("| Группа | Вопросов | Отказов | Выдуманных ссылок |")
    lines.append("|---|---:|---:|---:|")
    for group, stats in sorted(metrics.by_group.items()):
        title = GROUP_TITLES.get(group, group)
        lines.append(
            f"| {title} | {stats['total']} | {stats['refusals']} | {stats['invalid_citations']} |"
        )
    lines.append("")

    wrong_on_traps = [r for r in records if r.is_trap and not r.is_refusal]
    if wrong_on_traps:
        lines.append("## Ловушки, на которых система всё-таки ответила")
        lines.append("")
        lines.append("Самое важное место отчёта: здесь система выдумывает.")
        lines.append("")
        for r in wrong_on_traps:
            lines.append(f"**{r.question_id}**: {r.question}")
            lines.append("")
            lines.append(f"> {r.answer[:400]}")
            lines.append("")

    false_refusals = [r for r in records if not r.is_trap and r.is_refusal]
    if false_refusals:
        lines.append("## Отказы там, где ответ был")
        lines.append("")
        lines.append(
            "Осторожность полезна, но чрезмерная делает систему бесполезной. "
            "Отмечено, был ли нужный документ в контексте: если не был, виноват "
            "поиск, а не модель."
        )
        lines.append("")
        lines.append("| Вопрос | Нужный документ был найден? |")
        lines.append("|---|---|")
        for r in false_refusals:
            found = "да" if r.expected_document_was_retrieved else "**нет — промах поиска**"
            lines.append(f"| {r.question_id}: {r.question} | {found} |")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    settings = get_settings()
    questions = load_golden_set()

    print(f"Вопросов в наборе: {len(questions)}")
    print(f"Модель: {settings.llm_model}")
    print("Генерация занимает десятки минут — по одному ответу на вопрос.\n")

    records: list[AnswerRecord] = []
    started = time.monotonic()

    try:
        with connect(settings) as conn:
            embedder = Embedder(settings)
            model = OpenAICompatibleModel(settings)

            for number, question in enumerate(questions, start=1):
                hits = search(
                    conn, embedder, question.question,
                    method=settings.eval_search_method,
                    limit=settings.answer_context_chunks,
                    settings=settings,
                )
                answer = answer_question(model, question.question, hits, settings)
                records.append(make_record(question, answer))

                elapsed = time.monotonic() - started
                print(f"  {number}/{len(questions)} [{question.id}] "
                      f"{'отказ' if answer.is_refusal else 'ответ'} "
                      f"({elapsed / number:.0f} сек/вопрос)")

    except IndexMismatchError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1
    except LLMError as exc:
        print(f"\nМодель недоступна: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\nОШИБКА: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    metrics = compute_metrics(records)

    print("")
    print("=== Итог ===")
    print(f"Корректные отказы на ловушках: {metrics.refusal_rate_on_traps:.0%} "
          f"({metrics.correct_refusals}/{metrics.traps})")
    print(f"Ложные отказы:                 {metrics.false_refusal_rate:.0%} "
          f"({metrics.false_refusals}/{metrics.answerable})")
    print(f"Выдуманные ссылки:             {metrics.invalid_citation_rate:.0%} "
          f"({metrics.invalid_citations}/{metrics.total})")
    print(f"Точность цитирования:          {metrics.citation_precision:.0%} "
          f"({metrics.cited_expected}/{metrics.context_had_answer})")

    answers_path = settings.reports_dir / "answers.json"
    save_records(records, answers_path)
    print(f"\nОтветы сохранены: {answers_path}")

    report_path = settings.reports_dir / "generation_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(metrics, records, settings), encoding="utf-8")
    print(f"Отчёт: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
