"""Нарезка всего корпуса с проверкой инвариантов.

Запуск: python -m ragmdn.corpus.chunk_all

Проверяет то, что нельзя проверить юнит-тестами на придуманных данных:
инварианты должны держаться на всех 1323 документах, а не только на тех
примерах, которые пришли в голову автору. Команда возвращает ненулевой код,
если хоть один инвариант нарушен, — её можно ставить в CI.
"""

import sys
from statistics import median

from ragmdn.config import get_settings
from ragmdn.corpus.chunking import Chunk, chunk_document
from ragmdn.corpus.parse_all import parse_corpus

#: Фрагменты, которые печатаются целиком — чтобы прочитать глазами.
SAMPLE_COUNT = 4


def _is_code_only(chunk: Chunk) -> bool:
    text = chunk.text.strip()
    return text.startswith("```") and text.endswith("```") and text.count("```") == 2


def main() -> int:
    settings = get_settings()
    root = settings.raw_dir / "mdn-translated-content" / "files" / "ru"

    if not root.exists():
        print(
            "Корпус не найден. Сначала выполните: python -m ragmdn.corpus.cli",
            file=sys.stderr,
        )
        return 1

    print("Разбираю и нарезаю корпус...")
    parsed, failures = parse_corpus(root, settings)
    chunks = [chunk for doc in parsed for chunk in chunk_document(doc, settings)]

    if not chunks:
        print("ОШИБКА: не получено ни одного фрагмента", file=sys.stderr)
        return 1

    lengths = sorted(len(chunk.text) for chunk in chunks)
    embedding_lengths = sorted(len(chunk.embedding_input) for chunk in chunks)

    # Проверяется именно embedding_input: лимит модели тратится на него
    # целиком, вместе с путём заголовков.
    oversized = [c for c in chunks if len(c.embedding_input) > settings.chunk_max_chars]
    unbalanced = [c for c in chunks if c.text.count("```") % 2 != 0]
    blank = [c for c in chunks if not c.text.strip()]
    code_only = [c for c in chunks if _is_code_only(c)]
    short = [c for c in chunks if len(c.text) < settings.chunk_min_chars]

    print("")
    print("=== Сводка нарезки ===")
    print(f"Документов:             {len(parsed)}")
    print(f"Ошибок разбора:         {len(failures)}")
    print(f"Фрагментов:             {len(chunks)}")
    print(
        f"Длина фрагмента:        мин {lengths[0]}, медиана {int(median(lengths))}, "
        f"макс {lengths[-1]}"
    )
    print(f"С путём заголовков:     макс {embedding_lengths[-1]}")
    print("")
    print("--- Инварианты ---")
    print(f"Превышают потолок:      {len(oversized)}")
    print(f"Разорванный код:        {len(unbalanced)}")
    print(f"Пустые:                 {len(blank)}")
    print("")
    print("--- Наблюдения (не ошибки) ---")
    print(f"Только код:             {len(code_only)} ({100 * len(code_only) / len(chunks):.1f}%)")
    print(f"Короче минимума:        {len(short)} ({100 * len(short) / len(chunks):.1f}%)")

    violations = oversized + unbalanced + blank
    if violations:
        print(f"\nНАРУШЕНЫ ИНВАРИАНТЫ ({len(violations)}):", file=sys.stderr)
        for chunk in violations[:10]:
            print(f"  {chunk.slug} :: {chunk.heading_line}", file=sys.stderr)

    samples_path = settings.reports_dir / "chunk_samples.md"
    samples_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Примеры фрагментов", ""]
    lines.append(
        "Так выглядит то, что попадёт в векторную базу. Каждый фрагмент "
        "показан ровно в том виде, в каком уйдёт в модель эмбеддингов — "
        "вместе с путём заголовков в первой строке."
    )
    lines.append("")

    step = max(len(chunks) // (SAMPLE_COUNT + 1), 1)
    for index in range(SAMPLE_COUNT):
        chunk = chunks[step * (index + 1)]
        lines.append(f"## Фрагмент {index + 1}: {chunk.title}")
        lines.append("")
        lines.append(f"- Источник: {chunk.source_url}")
        lines.append(f"- Длина: {len(chunk.text)} символов")
        lines.append("")
        lines.append("````")
        lines.append(chunk.embedding_input)
        lines.append("````")
        lines.append("")

    samples_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nПримеры для чтения глазами: {samples_path}")

    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
