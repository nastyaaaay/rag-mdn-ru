"""Вопрос к системе из командной строки.

    python -m ragmdn.ask "как отфильтровать массив"          — ответ со ссылками
    python -m ragmdn.ask --hits-only "как отфильтровать"     — только найденные фрагменты
    python -m ragmdn.ask --compare "как отфильтровать"       — сравнить способы поиска

По умолчанию система ищет фрагменты и просит модель составить по ним ответ.
Режим `--hits-only` не обращается к модели вовсе — полезно, когда надо
посмотреть на выдачу поиска саму по себе или когда модель недоступна.
"""

import argparse
import functools
import sys

from ragmdn.answer import answer_question
from ragmdn.config import get_settings
from ragmdn.db import IndexMismatchError, connect
from ragmdn.embeddings import Embedder
from ragmdn.llm import LLMError, OpenAICompatibleModel
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
    parser = argparse.ArgumentParser(description="Вопрос по документации MDN")
    parser.add_argument("query", help="вопрос на русском языке")
    parser.add_argument("--method", choices=SEARCH_METHODS, default="vector",
                        help="способ поиска (по умолчанию vector — он выиграл по метрикам)")
    parser.add_argument("--limit", type=int, default=5, help="сколько фрагментов использовать")
    parser.add_argument("--hits-only", action="store_true",
                        help="только найденные фрагменты, без обращения к модели")
    parser.add_argument("--compare", action="store_true",
                        help="сравнить выдачу всех способов поиска (без генерации)")
    args = parser.parse_args()

    settings = get_settings()

    try:
        with connect(settings) as conn:
            embedder = Embedder(settings)

            if args.compare:
                for method in SEARCH_METHODS:
                    hits = search(conn, embedder, args.query,
                                  method=method, limit=args.limit, settings=settings)
                    _print_hits(method, hits)
                return 0

            hits = search(conn, embedder, args.query,
                          method=args.method, limit=args.limit, settings=settings)

            if args.hits_only:
                _print_hits(args.method, hits)
                return 0

            print(f"Найдено фрагментов: {len(hits)}. Спрашиваю модель "
                  f"({settings.llm_model})...")
            answer = answer_question(
                OpenAICompatibleModel(settings), args.query, hits, settings
            )

    except IndexMismatchError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1
    except LLMError as exc:
        print(f"\nМодель недоступна: {exc}", file=sys.stderr)
        print("Проверьте LLM_BASE_URL в .env или запустите с --hits-only.", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\nОШИБКА: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("База поднята и проиндексирована?", file=sys.stderr)
        return 1

    print("")
    print("=== Ответ ===")
    print(answer.text)

    if answer.source_urls:
        print("")
        print("Источники:")
        for url in answer.source_urls:
            print(f"  {url}")

    if answer.has_invalid_citation:
        print("")
        print("ВНИМАНИЕ: модель сослалась на несуществующий фрагмент — "
              "признак выдумывания.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
