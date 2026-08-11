"""Индексация корпуса: от скачанных файлов до строк в базе.

Запуск: python -m ragmdn.index_all

Здесь сходится весь конвейер предыдущих шагов — отбор документов, парсер,
нарезка, эмбеддинги, запись в базу. Операция разовая и небыстрая (минуты),
поэтому она печатает прогресс и заканчивается подробной сводкой: сколько
документов обработано, сколько пропущено и почему. Молчаливого «готово»
здесь быть не должно — если часть корпуса не доехала до базы, это обязано
быть видно сразу, а не всплыть потом в метриках.
"""

import functools
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Вывод этой команды почти всегда перенаправляют в файл (операция идёт
# минуты), а при перенаправлении Python буферизует stdout — прогресс
# не появляется вообще, и понять, работает ли программа, невозможно.
print = functools.partial(print, flush=True)  # noqa: A001 — намеренная замена

from ragmdn.config import Settings, get_settings
from ragmdn.corpus.chunking import Chunk, chunk_document
from ragmdn.corpus.frontmatter import FrontmatterError
from ragmdn.corpus.parser import ParseError, parse_document
from ragmdn.corpus.report import CorpusReport, DocumentStats, build_report
from ragmdn.db import (
    DocumentRow,
    connect,
    insert_chunks,
    insert_document,
    reset_index,
    write_index_parameters,
)
from ragmdn.embeddings import Embedder

#: По сколько фрагментов считать эмбеддинги за раз. Больше — быстрее, но
#: заметнее пики по памяти и реже обновляется прогресс.
BATCH_SIZE = 64


@dataclass
class IndexReport:
    documents_indexed: int = 0
    chunks_indexed: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return not self.failures and self.chunks_indexed > 0


def _collect_chunks(
    root: Path, report: CorpusReport, settings: Settings
) -> tuple[list[tuple[DocumentStats, list[Chunk]]], list[tuple[str, str]]]:
    """Разбирает и нарезает все отобранные документы."""
    prepared: list[tuple[DocumentStats, list[Chunk]]] = []
    failures: list[tuple[str, str]] = []

    for stats in report.kept(settings.min_cyrillic_ratio):
        try:
            raw = (root / stats.relative_path).read_text(encoding="utf-8")
            document = parse_document(raw)
        except (ParseError, FrontmatterError, OSError) as exc:
            failures.append((stats.relative_path, str(exc)))
            continue

        chunks = chunk_document(document, settings)
        if not chunks:
            failures.append((stats.relative_path, "после нарезки не осталось фрагментов"))
            continue

        prepared.append((stats, chunks))

    return prepared, failures


def index_corpus(root: Path, settings: Settings, embedder: Embedder) -> IndexReport:
    """Полная переиндексация корпуса."""
    started = time.monotonic()
    result = IndexReport()

    print("Отбираю документы...")
    corpus_report = build_report(root, settings)
    result.failures.extend(
        (err.relative_path, err.reason) for err in corpus_report.errors
    )

    print("Разбираю и нарезаю...")
    prepared, parse_failures = _collect_chunks(root, corpus_report, settings)
    result.failures.extend(parse_failures)

    total_chunks = sum(len(chunks) for _, chunks in prepared)
    print(f"Готово к индексации: {len(prepared)} документов, {total_chunks} фрагментов")

    with connect(settings) as conn:
        # Полная переиндексация: старые данные удаляются целиком, иначе
        # в базе смешались бы фрагменты, посчитанные разными настройками.
        reset_index(conn)
        write_index_parameters(conn, settings)

        processed = 0
        for stats, chunks in prepared:
            document_id = insert_document(
                conn,
                DocumentRow(
                    slug=chunks[0].slug,
                    title=chunks[0].title,
                    source_url=chunks[0].source_url,
                    area=stats.area,
                    cyrillic_ratio=stats.cyrillic_ratio,
                    char_count=stats.char_count,
                ),
            )

            for start in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[start : start + BATCH_SIZE]
                vectors = embedder.embed_passages([c.embedding_input for c in batch])
                insert_chunks(conn, document_id, batch, vectors)
                processed += len(batch)

                if processed % (BATCH_SIZE * 8) < BATCH_SIZE:
                    share = 100 * processed / total_chunks
                    elapsed = time.monotonic() - started
                    speed = processed / elapsed if elapsed else 0
                    print(
                        f"  {processed}/{total_chunks} фрагментов "
                        f"({share:.0f}%, {speed:.0f} фр/сек)"
                    )

            result.documents_indexed += 1
            result.chunks_indexed += len(chunks)

            # Фиксируем порциями, а не одной транзакцией на весь корпус.
            # Индексация идёт минуты: при сбое в конце единственная большая
            # транзакция откатилась бы целиком, и всю работу пришлось бы
            # повторять. Плюс так виден прогресс запросом к базе.
            if result.documents_indexed % 50 == 0:
                conn.commit()

    result.elapsed_seconds = time.monotonic() - started
    return result


def main() -> int:
    settings = get_settings()
    root = settings.raw_dir / "mdn-translated-content" / "files" / "ru"

    if not root.exists():
        print(
            "Корпус не найден. Сначала выполните: python -m ragmdn.corpus.cli",
            file=sys.stderr,
        )
        return 1

    print(f"Модель эмбеддингов: {settings.embedding_model}")
    print("При первом запуске модель скачивается (~2.24 ГБ).\n")

    try:
        report = index_corpus(root, settings, Embedder(settings))
    except Exception as exc:  # noqa: BLE001 — сюда попадают и сбои базы, и сбои модели
        print(f"\nИНДЕКСАЦИЯ ПРЕРВАНА: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print("")
    print("=== Сводка индексации ===")
    print(f"Документов в базе:   {report.documents_indexed}")
    print(f"Фрагментов в базе:   {report.chunks_indexed}")
    print(f"Пропущено:           {len(report.failures)}")
    print(f"Время:               {report.elapsed_seconds:.0f} сек")
    if report.chunks_indexed:
        print(f"Скорость:            {report.chunks_indexed / report.elapsed_seconds:.0f} фрагментов/сек")

    if report.failures:
        print(f"\nПРОПУЩЕННЫЕ ДОКУМЕНТЫ ({len(report.failures)}):", file=sys.stderr)
        for path, reason in report.failures[:20]:
            print(f"  {path}: {reason}", file=sys.stderr)

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
