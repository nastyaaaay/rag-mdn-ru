"""Прогон эталонного набора и отчёт о качестве поиска.

    python -m ragmdn.evaluation.run_retrieval
    python -m ragmdn.evaluation.run_retrieval --methods vector hybrid

Считает Recall@k и MRR по группам вопросов для каждого способа поиска
и сохраняет отчёт в reports/retrieval_report.md.
"""

import argparse
import functools
import sys

from ragmdn.config import get_settings
from ragmdn.db import IndexMismatchError, connect
from ragmdn.embeddings import Embedder
from ragmdn.evaluation.golden import load_golden_set
from ragmdn.evaluation.retrieval import (
    RECALL_AT,
    aggregate,
    evaluate_question,
    render_markdown,
)
from ragmdn.search import SEARCH_METHODS, search

print = functools.partial(print, flush=True)  # noqa: A001

#: Сколько результатов запрашивать. Должно покрывать наибольшее k в Recall.
SEARCH_LIMIT = max(RECALL_AT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Оценка качества поиска")
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=SEARCH_METHODS,
        default=list(SEARCH_METHODS),
        help="какие способы поиска оценивать",
    )
    args = parser.parse_args()

    settings = get_settings()
    questions = load_golden_set()
    scored = [q for q in questions if not q.is_trap]
    print(f"Вопросов в наборе: {len(questions)} (из них с ответом: {len(scored)})")

    metrics_by_method = {}
    outcomes_by_method = {}

    try:
        with connect(settings) as conn:
            embedder = Embedder(settings)

            for method in args.methods:
                print(f"\nСпособ: {method}")
                outcomes = []
                for index, question in enumerate(questions, start=1):
                    hits = search(
                        conn, embedder, question.question,
                        method=method, limit=SEARCH_LIMIT,
                        settings=settings if index == 1 else None,
                    )
                    outcomes.append(evaluate_question(question, hits))
                    if index % 10 == 0:
                        print(f"  {index}/{len(questions)}")

                outcomes_by_method[method] = outcomes
                metrics_by_method[method] = aggregate(outcomes)

    except IndexMismatchError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\nОШИБКА: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("База поднята и проиндексирована?", file=sys.stderr)
        return 1

    print("")
    print("=== Итог ===")
    for method, metrics in metrics_by_method.items():
        total = metrics.get("ВСЕГО")
        if total:
            print(
                f"{method:>9}: R@1={total.recall[1]:.0%}  R@5={total.recall[5]:.0%}  "
                f"MRR={total.mrr:.3f}  промахов={len(total.misses)}"
            )

    print("")
    print("По группам (Recall@5):")
    groups = sorted({g for m in metrics_by_method.values() for g in m if g != "ВСЕГО"})
    for group in groups:
        parts = [
            f"{method}={metrics[group].recall[5]:.0%}"
            for method, metrics in metrics_by_method.items()
            if group in metrics
        ]
        print(f"  {group:>8}: {'  '.join(parts)}")

    report_path = settings.reports_dir / "retrieval_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_markdown(metrics_by_method, outcomes_by_method), encoding="utf-8"
    )
    print(f"\nОтчёт: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
