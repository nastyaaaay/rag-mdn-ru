"""Работа с базой: подключение, запись фрагментов, контроль соответствия.

Главная забота этого модуля — не дать индексу и коду разойтись незаметно.
Если базу построили одной моделью эмбеддингов, а вектор запроса считают
другой, поиск не сломается с ошибкой: он продолжит работать и выдавать
правдоподобную чепуху. Такое расхождение обнаруживается только по
испорченным метрикам, причём не сразу. Поэтому параметры индексации
записываются в таблицу `index_meta` и сверяются при каждом обращении.
"""

import hashlib
import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass

import psycopg

from ragmdn.config import Settings
from ragmdn.corpus.chunking import Chunk


class IndexMismatchError(RuntimeError):
    """Индекс в базе построен не теми параметрами, что заданы в настройках."""


@dataclass(frozen=True)
class DocumentRow:
    """Метаданные документа, как они лежат в базе."""

    slug: str
    title: str
    source_url: str
    area: str
    cyrillic_ratio: float
    char_count: int


def content_hash(text: str) -> str:
    """Хеш содержимого фрагмента.

    Нужен, чтобы при повторной индексации понимать, изменился ли текст,
    и чтобы ловить случайные дубликаты.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@contextmanager
def connect(settings: Settings, *, connect_timeout: int | None = None) -> Iterator[psycopg.Connection]:
    """Подключение к базе. Транзакция фиксируется при выходе без ошибок.

    Таймаут обязателен: без него попытка подключиться к неподнятой базе
    висит очень долго вместо того, чтобы честно упасть. Для тестов это
    означало бы зависший прогон вместо аккуратного пропуска.
    """
    with psycopg.connect(
        settings.database_url,
        connect_timeout=connect_timeout or settings.db_connect_timeout,
    ) as conn:
        yield conn


def index_parameters(settings: Settings) -> dict[str, str]:
    """Параметры, при изменении которых индекс становится недействительным.

    Модель и размерность — потому что векторы несопоставимы между моделями.
    Размеры фрагментов и порог фильтра — потому что от них зависит, что
    вообще попало в базу, и сравнивать метрики между разными нарезками
    нельзя, не зная этих чисел.
    """
    return {
        "embedding_model": settings.embedding_model,
        "embedding_dim": str(settings.embedding_dim),
        "chunk_target_chars": str(settings.chunk_target_chars),
        "chunk_max_chars": str(settings.chunk_max_chars),
        "chunk_min_chars": str(settings.chunk_min_chars),
        "min_cyrillic_ratio": str(settings.min_cyrillic_ratio),
    }


def write_index_parameters(conn: psycopg.Connection, settings: Settings) -> None:
    """Сохраняет параметры индексации, перезаписывая прежние."""
    with conn.cursor() as cur:
        for key, value in index_parameters(settings).items():
            cur.execute(
                """
                INSERT INTO index_meta (key, value, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value, updated_at = now()
                """,
                (key, value),
            )


def read_index_parameters(conn: psycopg.Connection) -> dict[str, str]:
    with conn.cursor() as cur:
        cur.execute("SELECT key, value FROM index_meta")
        return {key: value for key, value in cur.fetchall()}


def verify_index_matches_settings(conn: psycopg.Connection, settings: Settings) -> None:
    """Проверяет, что база построена теми же параметрами, что заданы сейчас.

    Поднимает IndexMismatchError с перечнем расхождений. Вызывается перед
    поиском: лучше остановиться с внятным сообщением, чем молча искать
    векторами одной модели по индексу, построенному другой.
    """
    stored = read_index_parameters(conn)
    if not stored:
        raise IndexMismatchError(
            "в базе нет параметров индексации — похоже, индексация ещё не выполнялась. "
            "Запустите: python -m ragmdn.index_all"
        )

    expected = index_parameters(settings)
    differences = [
        f"  {key}: в базе {stored.get(key, '<нет>')!r}, в настройках {value!r}"
        for key, value in expected.items()
        if stored.get(key) != value
    ]
    if differences:
        raise IndexMismatchError(
            "Параметры индекса не совпадают с текущими настройками:\n"
            + "\n".join(differences)
            + "\n\nВекторы разных моделей несопоставимы: поиск продолжил бы работать, "
            "но выдавал бы бессмыслицу. Переиндексируйте базу: python -m ragmdn.index_all"
        )


def reset_index(conn: psycopg.Connection) -> None:
    """Очищает индекс перед полной переиндексацией.

    TRUNCATE вместо DELETE: он быстрее и сразу сбрасывает счётчики
    идентификаторов. CASCADE — потому что chunks ссылается на documents.
    """
    with conn.cursor() as cur:
        cur.execute("TRUNCATE documents, chunks RESTART IDENTITY CASCADE")


def insert_document(conn: psycopg.Connection, document: DocumentRow) -> int:
    """Записывает документ и возвращает его идентификатор."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (slug, title, source_url, area, cyrillic_ratio, char_count)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                title = EXCLUDED.title,
                source_url = EXCLUDED.source_url,
                area = EXCLUDED.area,
                cyrillic_ratio = EXCLUDED.cyrillic_ratio,
                char_count = EXCLUDED.char_count,
                indexed_at = now()
            RETURNING id
            """,
            (
                document.slug,
                document.title,
                document.source_url,
                document.area,
                document.cyrillic_ratio,
                document.char_count,
            ),
        )
        row = cur.fetchone()
        assert row is not None  # RETURNING всегда даёт строку
        return row[0]


def insert_chunks(
    conn: psycopg.Connection,
    document_id: int,
    chunks: Sequence[Chunk],
    embeddings: Sequence[Sequence[float]],
) -> int:
    """Записывает фрагменты вместе с их векторами.

    Число фрагментов и число векторов обязано совпадать: рассинхрон означал бы,
    что тексту приписан чужой вектор — самая опасная из возможных ошибок,
    потому что поиск продолжит работать и никто ничего не заметит.
    """
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"фрагментов {len(chunks)}, а векторов {len(embeddings)} — "
            "тексту был бы приписан чужой вектор"
        )

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO chunks
                (document_id, ordinal, heading_path, content, char_count, content_hash, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (document_id, ordinal) DO UPDATE SET
                heading_path = EXCLUDED.heading_path,
                content = EXCLUDED.content,
                char_count = EXCLUDED.char_count,
                content_hash = EXCLUDED.content_hash,
                embedding = EXCLUDED.embedding
            """,
            [
                (
                    document_id,
                    chunk.ordinal,
                    chunk.heading_line,
                    chunk.text,
                    len(chunk.text),
                    content_hash(chunk.text),
                    # pgvector принимает вектор в виде строки '[1,2,3]'
                    json.dumps(list(vector)),
                )
                for chunk, vector in zip(chunks, embeddings)
            ],
        )
    return len(chunks)


def count_rows(conn: psycopg.Connection) -> tuple[int, int]:
    """Сколько документов и фрагментов лежит в базе."""
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM documents")
        documents = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM chunks")
        chunks = cur.fetchone()[0]
    return documents, chunks
