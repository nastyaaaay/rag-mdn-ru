"""Точка входа шага 2: скачать корпус и построить отчёт о его качестве.

Запуск: python -m ragmdn.corpus.cli
"""

import sys

from ragmdn.config import get_settings
from ragmdn.corpus.download import DownloadError, sync_corpus
from ragmdn.corpus.report import build_report, render_markdown, write_csv


def main() -> int:
    settings = get_settings()

    print(f"Синхронизирую разделы {list(settings.mdn_areas)} из {settings.mdn_repo}...")
    try:
        root = sync_corpus(settings)
    except DownloadError as exc:
        print(f"ОШИБКА загрузки: {exc}", file=sys.stderr)
        return 1

    print(f"Разбираю документы в {root}...")
    report = build_report(root, settings)

    threshold = settings.min_cyrillic_ratio
    kept = report.kept(threshold)
    excluded = report.excluded_by_language(threshold)
    stubs = report.stubs()

    print("")
    print("=== Сводка ===")
    print(f"Найдено файлов:        {report.total_found}")
    print(f"Успешно разобрано:     {len(report.documents)}")
    print(f"Ошибок разбора:        {len(report.errors)}")
    print(f"Заглушек:               {len(stubs)}")
    print(f"Исключено по языку:    {len(excluded)} (порог {threshold:.0%})")
    print(f"Включено в индекс:     {len(kept)}")

    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    csv_path = settings.reports_dir / "corpus_stats.csv"
    write_csv(report, csv_path)
    print(f"\nПодробная таблица по документам: {csv_path}")

    report_path = settings.reports_dir / "corpus_report.md"
    report_path.write_text(render_markdown(report, settings), encoding="utf-8")
    print(f"Markdown-отчёт: {report_path}")

    if report.errors:
        print(
            f"\nВНИМАНИЕ: {len(report.errors)} файлов не разобрались — "
            "смотрите раздел «Ошибки разбора» в отчёте.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
