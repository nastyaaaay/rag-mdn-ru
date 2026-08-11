"""Тесты поиска.

Работают на маленьком наборе фрагментов, который тест сам кладёт в базу.
Векторы задаются вручную — так поведение ранжирования проверяется точно,
без зависимости от того, что именно выдаст настоящая модель.
"""

from collections.abc import Iterable, Sequence

import pytest

from ragmdn.config import Settings
from ragmdn.db import DocumentRow, connect, insert_chunks, insert_document, reset_index
from ragmdn.embeddings import Embedder
from ragmdn.search import RRF_K, search, search_fulltext, search_hybrid, search_vector
from tests.test_db import make_chunk


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def unit_vector(dim: int, axis: int) -> list[float]:
    """Вектор, направленный вдоль одной оси — удобно для точных проверок."""
    vector = [0.0] * dim
    vector[axis] = 1.0
    return vector


class FixedBackend:
    """Отдаёт заранее заданный вектор — что бы ни попросили."""

    def __init__(self, vector: Sequence[float]):
        self.vector = list(vector)

    def embed(self, texts: Iterable[str]) -> Iterable[Sequence[float]]:
        return [self.vector for _ in list(texts)]


@pytest.fixture
def filled_db(database_available, test_settings):
    """Тестовая база с тремя фрагментами: два про массивы, один про строки."""
    if database_available is not None:
        pytest.skip(f"база недоступна ({database_available})")

    settings = test_settings
    dim = settings.embedding_dim

    with connect(settings) as conn:
        reset_index(conn)
        document_id = insert_document(
            conn,
            DocumentRow(
                slug="Web/JavaScript/Reference/Global_Objects/Array/filter",
                title="Array.prototype.filter()",
                source_url="https://developer.mozilla.org/ru/docs/Web/JS/filter",
                area="web/javascript",
                cyrillic_ratio=0.85,
                char_count=500,
            ),
        )
        chunks = [
            make_chunk(0, "Метод фильтрует массив и создаёт новый массив элементов."),
            make_chunk(1, "Метод преобразует каждый элемент массива в новое значение."),
            make_chunk(2, "Строка разбивается на подстроки по указанному разделителю."),
        ]
        vectors = [unit_vector(dim, 0), unit_vector(dim, 1), unit_vector(dim, 2)]
        insert_chunks(conn, document_id, chunks, vectors)
        yield conn, settings


@pytest.mark.db
def test_vector_search_returns_closest_first(filled_db):
    conn, settings = filled_db
    # Запрос точно по направлению первого фрагмента
    embedder = Embedder(settings, FixedBackend(unit_vector(settings.embedding_dim, 0)))

    hits = search_vector(conn, embedder, "неважно", limit=3)

    assert hits[0].content.startswith("Метод фильтрует")
    assert hits[0].score > hits[1].score, "похожесть должна убывать"


@pytest.mark.db
def test_vector_search_score_is_similarity_not_distance(filled_db):
    """В score должна лежать похожесть: больше — лучше."""
    conn, settings = filled_db
    embedder = Embedder(settings, FixedBackend(unit_vector(settings.embedding_dim, 0)))

    hits = search_vector(conn, embedder, "неважно", limit=1)

    assert hits[0].score == pytest.approx(1.0, abs=1e-6)


@pytest.mark.db
def test_fulltext_search_finds_by_word_form(filled_db):
    """Русская морфология: «разделителя» в тексте, «разделитель» в запросе."""
    conn, _ = filled_db

    hits = search_fulltext(conn, "разделитель", limit=5)

    assert len(hits) == 1
    assert "подстроки" in hits[0].content


@pytest.mark.db
def test_fulltext_search_returns_nothing_for_absent_words(filled_db):
    conn, _ = filled_db

    assert search_fulltext(conn, "чебурашка крокодил", limit=5) == []


@pytest.mark.db
def test_hybrid_ranks_document_found_by_both_methods_first(filled_db):
    """Фрагмент, найденный обоими способами, должен обойти найденный одним."""
    conn, settings = filled_db
    # Вектор указывает на первый фрагмент, и слово «фильтрует» есть только в нём
    embedder = Embedder(settings, FixedBackend(unit_vector(settings.embedding_dim, 0)))

    hits = search_hybrid(conn, embedder, "фильтрует", limit=3)

    assert hits[0].content.startswith("Метод фильтрует")


@pytest.mark.db
def test_hybrid_still_works_when_words_match_nothing(filled_db):
    """Если словесный поиск пуст, гибрид обязан опереться на векторный."""
    conn, settings = filled_db
    embedder = Embedder(settings, FixedBackend(unit_vector(settings.embedding_dim, 2)))

    hits = search_hybrid(conn, embedder, "абракадабра", limit=3)

    assert hits, "гибрид не должен возвращать пустоту из-за одного пустого списка"
    assert hits[0].content.startswith("Строка разбивается")


@pytest.mark.db
def test_hybrid_score_uses_rrf_formula(filled_db):
    """Верхний результат, найденный только одним способом, получает 1/(K+1)."""
    conn, settings = filled_db
    embedder = Embedder(settings, FixedBackend(unit_vector(settings.embedding_dim, 2)))

    hits = search_hybrid(conn, embedder, "абракадабра", limit=1)

    assert hits[0].score == pytest.approx(1 / (RRF_K + 1))


@pytest.mark.db
def test_search_rejects_unknown_method(filled_db):
    conn, settings = filled_db
    embedder = Embedder(settings, FixedBackend(unit_vector(settings.embedding_dim, 0)))

    with pytest.raises(ValueError, match="неизвестный способ"):
        search(conn, embedder, "запрос", method="телепатия")


@pytest.mark.db
def test_hits_carry_source_url(filled_db):
    """Ответ обязан ссылаться на источник — это требование к системе."""
    conn, settings = filled_db
    embedder = Embedder(settings, FixedBackend(unit_vector(settings.embedding_dim, 0)))

    hits = search_vector(conn, embedder, "неважно", limit=1)

    assert hits[0].source_url.startswith("https://developer.mozilla.org/ru/docs/")
