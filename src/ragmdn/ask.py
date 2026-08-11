"""Поиск из командной строки — чтобы посмотреть выдачу глазами.

    python -m ragmdn.ask "как отфильтровать массив"
    python -m ragmdn.ask --method vector "как отфильтровать массив"
    python -m ragmdn.ask --compare "как отфильтровать массив"

Режим `--compare` показывает выдачу всех трёх способов рядом. Метрики
появятся на шаге 9, но прежде чем мерить, полезно просто посмотреть,
что система вообще находит — цифры без этого легко трактовать неверно.
"""

import argparse
import functools
import sys

from ragmdn.config import get_settings
from ragmdn.db import IndexMismatchError, connect
from ragmdn.embeddings import Embedder
from ragmdn.search import SEARCH_METHODS, search

print = functools.partial(print, flush=True)  # noqa: A001


def _print_hits(title: str, hits) -> None:
    print(f"\n--- {title} ---")
    if not hits:
        print("  ничего не найдено")
        return
    for position, hit in enumerate(hits, start=1):
        print(f"{position}. {hit.short}")
        print(f"   {hit.source_url}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Поиск по индексу документации MDN")
    parser.add_argument("query", help="вопрос на русском языке")
    parser.add_argument(
        "--method",
        choices=SEARCH_METHODS,
        default="hybrid",
        help="способ поиска (по умолчанию hybrid)",
    )
    parser.add_argument("--limit", type=int, default=5, help="сколько фрагментов показать")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="показать выдачу всех трёх способов для сравнения",
    )
    args = parser.parse_args()

    settings = get_settings()

    try:
        with connect(settings) as conn:
            embedder = Embedder(settings)

            if args.compare:
                for method in SEARCH_METHODS:
                    hits = search(
                        conn, embedder, args.query,
                        method=method, limit=args.limit, settings=settings,
                    )
                    _print_hits(method, hits)
            else:
                hits = search(
                    conn, embedder, args.query,
                    method=args.method, limit=args.limit, settings=settings,
                )
                _print_hits(args.method, hits)

    except IndexMismatchError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\nОШИБКА: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("База поднята? Проверьте: docker compose up -d", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
