"""Прогон парсера по всему корпусу с проверкой результата.

Запуск: python -m ragmdn.corpus.parse_all

Отдельная команда, а не часть индексации: парсер надо проверить на всех
документах до того, как результат уедет в базу. Главное, что она отвечает, —
не осталось ли незнакомых макросов и не развалился ли разбор где-нибудь
в середине корпуса.
"""

import sys
from collections import Counter
from pathlib import Path

from ragmdn.config import Settings, get_settings
from ragmdn.corpus.frontmatter import FrontmatterError
from ragmdn.corpus.parser import ParsedDocument, ParseError, parse_document
from ragmdn.corpus.report import build_report

#: Документы, которые печатаются целиком для чтения глазами.
SAMPLE_SLUGS = (
    "Web/JavaScript/Reference/Global_Objects/Array/filter",
    "Web/CSS/Reference/Properties/flex-wrap",
    "Glossary/AJAX",
)


def parse_corpus(
    root: Path, settings: Settings
) -> tuple[list[ParsedDocument], list[tuple[str, str]]]:
    """Разбирает все документы, прошедшие фильтры качества."""
    report = build_report(root, settings)
    kept = report.kept(settings.min_cyrillic_ratio)

    parsed: list[ParsedDocument] = []
    failures: list[tuple[str, str]] = []

    for stats in kept:
        path = root / stats.relative_path
        try:
            parsed.append(parse_document(path.read_text(encoding="utf-8")))
        except (ParseError, FrontmatterError, OSError) as exc:
            failures.append((stats.relative_path, str(exc)))

    return parsed, failures


def main() -> int:
    settings = get_settings()
    root = settings.raw_dir / "mdn-translated-content" / "files" / "ru"

    if not root.exists():
        print(
            "Корпус не найден. Сначала выполните: python -m ragmdn.corpus.cli",
            file=sys.stderr,
        )
        return 1

    print("Разбираю корпус...")
    parsed, failures = parse_corpus(root, settings)

    unknown_macros: Counter[str] = Counter()
    for doc in parsed:
        unknown_macros.update(doc.unknown_macros)

    section_counts = [len(doc.sections) for doc in parsed]
    text_lengths = [len(doc.text) for doc in parsed]
    empty_docs = [doc for doc in parsed if not doc.text.strip()]

    print("")
    print("=== Сводка разбора ===")
    print(f"Разобрано документов:   {len(parsed)}")
    print(f"Ошибок разбора:         {len(failures)}")
    print(f"Пустых после разбора:   {len(empty_docs)}")
    print(f"Неизвестных макросов:   {len(unknown_macros)}")
    if section_counts:
        print(
            f"Разделов на документ:   "
            f"мин {min(section_counts)}, медиана {sorted(section_counts)[len(section_counts) // 2]}, "
            f"макс {max(section_counts)}"
        )
        print(
            f"Длина текста:           "
            f"мин {min(text_lengths)}, медиана {sorted(text_lengths)[len(text_lengths) // 2]}, "
            f"макс {max(text_lengths)} символов"
        )

    if unknown_macros:
        print("\nНЕИЗВЕСТНЫЕ МАКРОСЫ (нужно добавить в macros.py):", file=sys.stderr)
        for name, count in unknown_macros.most_common(20):
            print(f"  {{{{{name}}}}}: {count}", file=sys.stderr)

    if failures:
        print(f"\nОШИБКИ РАЗБОРА ({len(failures)}):", file=sys.stderr)
        for path, reason in failures[:20]:
            print(f"  {path}: {reason}", file=sys.stderr)

    if empty_docs:
        print(f"\nПУСТЫЕ ПОСЛЕ РАЗБОРА ({len(empty_docs)}):", file=sys.stderr)
        for doc in empty_docs[:20]:
            print(f"  {doc.slug}", file=sys.stderr)

    # Примеры для чтения глазами — без них проверить парсер невозможно.
    by_slug = {doc.slug: doc for doc in parsed}
    samples_path = settings.reports_dir / "parsed_samples.md"
    samples_path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Примеры разобранных документов", ""]
    lines.append("Так текст выглядит после парсера — именно это попадёт в индекс.")
    lines.append("")
    for slug in SAMPLE_SLUGS:
        doc = by_slug.get(slug)
        if doc is None:
            lines.append(f"## {slug}\n\n*документ не найден в корпусе*\n")
            continue
        lines.append(f"## {doc.title}")
        lines.append("")
        lines.append(f"Источник: {doc.source_url}")
        lines.append("")
        for section in doc.sections:
            lines.append(f"### `{section.heading_line}`")
            lines.append("")
            lines.append("```")
            lines.append(section.text)
            lines.append("```")
            lines.append("")

    samples_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nПримеры для чтения глазами: {samples_path}")

    return 1 if (unknown_macros or failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
