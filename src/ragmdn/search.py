"""Поиск по индексу: векторный, полнотекстовый и гибридный.

Три способа сделаны не для красоты, а потому что на шаге 12 их надо честно
сравнить между собой. Заранее неизвестно, какой окажется лучше на этом
корпусе: у векторного и словесного поиска разные слабые места.

* **Векторный** ищет по смыслу. Находит ответ, даже если в вопросе нет ни
  одного слова из документа. Но плохо различает близкие по смыслу страницы —
  а в справочнике MDN их очень много (`filter` против `map`).
* **Полнотекстовый** ищет по словам с учётом русской морфологии. Точен, когда
  человек знает нужный термин, и бесполезен, когда спрашивает своими словами.
* **Гибридный** объединяет оба списка. Используется reciprocal rank fusion:
  документ тем выше, чем выше его позиции в обоих списках. Способ хорош тем,
  что не требует сводить к общей шкале «расстояние между векторами» и «вес
  совпадения слов» — величины, которые сравнивать напрямую бессмысленно.
"""

from dataclasses import dataclass

import psycopg

from ragmdn.config import Settings
from ragmdn.db import vector_literal, verify_index_matches_settings
from ragmdn.embeddings import Embedder

#: Константа сглаживания в reciprocal rank fusion. Значение 60 — принятое
#: по умолчанию в литературе: оно снижает влияние самых верхних позиций,
#: чтобы один список не подавлял другой целиком.
RRF_K = 60


@dataclass(frozen=True)
class SearchHit:
    """Найденный фрагмент."""

    chunk_id: int
    slug: str
    title: str
    source_url: str
    heading_path: str
    content: str
    score: float

    @property
    def short(self) -> str:
        """Однострочное представление для вывода в консоль."""
        preview = " ".join(self.content.split())[:100]
        return f"[{self.score:.4f}] {self.heading_path} — {preview}…"


_SELECT_FIELDS = """
    c.id, d.slug, d.title, d.source_url, c.heading_path, c.content
"""

#: Условие, отсекающее фрагменты, состоящие из одного лишь кода.
#: Таких в индексе 12% — следствие того, что код расходует лимит модели
#: вдвое быстрее прозы и потому чаще не помещается вместе с ней.
#: Гипотеза, которую проверяет шаг 12: они забивают выдачу и мешают
#: находить содержательные фрагменты.
#: Знак процента удвоен: psycopg считает одиночный `%` началом подстановки
#: параметра и отказывается выполнять такой запрос.
_EXCLUDE_CODE_ONLY = (
    "AND NOT (btrim(c.content) LIKE '```%%' AND btrim(c.content) LIKE '%%```')"
)


def search_vector(
    conn: psycopg.Connection,
    embedder: Embedder,
    query: str,
    limit: int = 5,
    *,
    exclude_code_only: bool = False,
) -> list[SearchHit]:
    """Поиск по смыслу через pgvector.

    Оператор `<=>` — косинусное расстояние: 0 у одинаковых векторов, 2 у
    противоположных. Для оценки удобнее похожесть (больше — лучше), поэтому
    в score кладётся `1 - расстояние`.
    """
    query_vector = vector_literal(embedder.embed_query(query))
    code_filter = _EXCLUDE_CODE_ONLY if exclude_code_only else ""

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_SELECT_FIELDS}, 1 - (c.embedding <=> %s::vector) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE TRUE {code_filter}
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
            """,
            (query_vector, query_vector, limit),
        )
        return [SearchHit(*row) for row in cur.fetchall()]


def search_fulltext(
    conn: psycopg.Connection, query: str, limit: int = 5
) -> list[SearchHit]:
    """Поиск по словам с русской морфологией.

    `plainto_tsquery` разбирает обычную человеческую фразу, приводит слова
    к основам и соединяет их через «И». Знаки препинания и стоп-слова
    отбрасываются сами.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_SELECT_FIELDS},
                   ts_rank(c.content_tsv, plainto_tsquery('russian', %s)) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.content_tsv @@ plainto_tsquery('russian', %s)
            ORDER BY score DESC
            LIMIT %s
            """,
            (query, query, limit),
        )
        return [SearchHit(*row) for row in cur.fetchall()]


def search_hybrid(
    conn: psycopg.Connection, embedder: Embedder, query: str, limit: int = 5
) -> list[SearchHit]:
    """Объединение векторного и словесного поиска через reciprocal rank fusion.

    Берётся расширенная выдача каждого способа, затем каждый фрагмент получает
    сумму `1 / (RRF_K + позиция)` по обоим спискам. Фрагмент, попавший в оба,
    поднимается выше тех, что нашлись лишь одним способом.
    """
    # Берём с запасом: фрагмент может быть третьим в одном списке и десятым
    # в другом, и именно такие обычно оказываются самыми удачными.
    pool = max(limit * 4, 20)
    vector_hits = search_vector(conn, embedder, query, pool)
    text_hits = search_fulltext(conn, query, pool)

    scores: dict[int, float] = {}
    hits_by_id: dict[int, SearchHit] = {}

    for hits in (vector_hits, text_hits):
        for position, hit in enumerate(hits, start=1):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1 / (RRF_K + position)
            hits_by_id[hit.chunk_id] = hit

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [
        SearchHit(
            chunk_id=hits_by_id[chunk_id].chunk_id,
            slug=hits_by_id[chunk_id].slug,
            title=hits_by_id[chunk_id].title,
            source_url=hits_by_id[chunk_id].source_url,
            heading_path=hits_by_id[chunk_id].heading_path,
            content=hits_by_id[chunk_id].content,
            score=score,
        )
        for chunk_id, score in ranked[:limit]
    ]


#: Способы поиска, доступные по имени — нужно для сравнения на шаге 12.
#: `vector_nocode` — тот же векторный, но без фрагментов из чистого кода.
SEARCH_METHODS = ("vector", "fulltext", "hybrid", "vector_nocode")


def search(
    conn: psycopg.Connection,
    embedder: Embedder,
    query: str,
    *,
    method: str = "hybrid",
    limit: int = 5,
    settings: Settings | None = None,
) -> list[SearchHit]:
    """Поиск выбранным способом.

    Если переданы настройки, сначала проверяется, что индекс построен теми же
    параметрами. Без этой проверки поиск по индексу от другой модели работал
    бы молча и выдавал бы правдоподобную чепуху.
    """
    if settings is not None:
        verify_index_matches_settings(conn, settings)

    if method == "vector":
        return search_vector(conn, embedder, query, limit)
    if method == "vector_nocode":
        return search_vector(conn, embedder, query, limit, exclude_code_only=True)
    if method == "fulltext":
        return search_fulltext(conn, query, limit)
    if method == "hybrid":
        return search_hybrid(conn, embedder, query, limit)

    raise ValueError(f"неизвестный способ поиска: {method!r}, доступны {SEARCH_METHODS}")
