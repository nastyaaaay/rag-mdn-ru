"""Тесты слоя базы данных.

Тесты, помеченные `@pytest.mark.db`, требуют поднятой базы
(`docker compose up -d`). Без неё они пропускаются, а не падают: обычный
прогон `pytest` должен работать и на машине без Docker.

Запустить только их:      pytest -m db
Запустить всё кроме них:  pytest -m "not db"
"""

import re
from pathlib import Path

import pytest

from ragmdn.config import PROJECT_ROOT, Settings
from ragmdn.corpus.chunking import Chunk
from ragmdn.db import (
    DocumentRow,
    IndexMismatchError,
    connect,
    content_hash,
    count_rows,
    index_parameters,
    insert_chunks,
    insert_document,
    reset_index,
    verify_index_matches_settings,
    write_index_parameters,
)


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


# --- Тесты без базы ------------------------------------------------------


def test_schema_dimension_matches_settings():
    """Размерность вектора продублирована в SQL и в настройках Python.

    Убрать дублирование нельзя — SQL не читает конфигурацию Python.
    Значит нужен тест, который падает, если значения развели.
    """
    schema = (PROJECT_ROOT / "db" / "init" / "01-schema.sql").read_text(encoding="utf-8")
    match = re.search(r"embedding\s+vector\((\d+)\)", schema)

    assert match is not None, "в схеме не найден столбец embedding"
    assert int(match.group(1)) == make_settings().embedding_dim


def test_vector_literal_formats_plain_numbers():
    """Регрессия: numpy 2 представляет числа как np.float64(0.1).

    Через str(list) вектор превращался в строку с np.float64(...), которую
    база отвергает. Ломалось это не при записи, а при первом поиске — то есть
    далеко от места, где ошибка сделана.
    """
    from ragmdn.db import vector_literal

    literal = vector_literal([0.1, -0.25, 3.0])

    assert "np.float64" not in literal
    assert literal == "[0.1, -0.25, 3.0]"


def test_vector_literal_handles_numpy_scalars():
    from ragmdn.db import vector_literal

    numpy = pytest.importorskip("numpy")
    literal = vector_literal(numpy.array([0.5, -1.5], dtype=numpy.float64))

    assert "np.float64" not in literal
    assert literal == "[0.5, -1.5]"


def test_tests_never_touch_the_working_database(test_settings):
    """Страховка от очень дорогой ошибки.

    Тесты очищают таблицы перед проверкой. Пока они ходили в рабочую базу,
    один прогон `pytest` стирал результат часовой индексации. Если кто-то
    случайно вернёт рабочий адрес — этот тест упадёт первым.
    """
    working = Settings(_env_file=None).database_url

    assert test_settings.database_url != working
    assert test_settings.database_url.endswith("_test")


def test_content_hash_is_stable_and_distinguishing():
    assert content_hash("текст") == content_hash("текст")
    assert content_hash("текст") != content_hash("текст ")


def test_index_parameters_include_model_and_chunking():
    params = index_parameters(make_settings())

    assert params["embedding_model"] == "intfloat/multilingual-e5-large"
    assert params["embedding_dim"] == "1024"
    assert "chunk_max_chars" in params
    assert "min_cyrillic_ratio" in params


# --- Тесты с базой -------------------------------------------------------


@pytest.fixture
def db(database_available, test_settings):
    """Подключение к ТЕСТОВОЙ базе; пропускает тест, если она недоступна."""
    if database_available is not None:
        pytest.skip(f"база недоступна ({database_available}); поднимите: docker compose up -d")
    with connect(test_settings) as conn:
        yield conn


@pytest.mark.db
def test_write_and_read_index_parameters(db):
    settings = make_settings()
    write_index_parameters(db, settings)

    verify_index_matches_settings(db, settings)  # не должно поднять исключение


@pytest.mark.db
def test_mismatched_model_is_detected(db):
    """Ключевая защита: подмена модели должна остановить работу.

    Без этой проверки поиск продолжил бы работать, сравнивая несопоставимые
    векторы, и выдавал бы правдоподобный мусор.
    """
    write_index_parameters(db, make_settings())
    other = make_settings(embedding_model="совершенно/другая-модель")

    with pytest.raises(IndexMismatchError, match="embedding_model"):
        verify_index_matches_settings(db, other)


@pytest.mark.db
def test_insert_document_and_chunks_roundtrip(db, make_chunk):
    settings = make_settings()
    reset_index(db)

    document_id = insert_document(
        db,
        DocumentRow(
            slug="Web/Test",
            title="Тест",
            source_url="https://developer.mozilla.org/ru/docs/Web/Test",
            area="web/javascript",
            cyrillic_ratio=0.8,
            char_count=100,
        ),
    )
    chunks = [make_chunk(0, "Первый фрагмент."), make_chunk(1, "Второй фрагмент.")]
    vectors = [[0.1] * settings.embedding_dim, [0.2] * settings.embedding_dim]

    written = insert_chunks(db, document_id, chunks, vectors)

    assert written == 2
    assert count_rows(db) == (1, 2)


@pytest.mark.db
def test_chunk_and_vector_count_must_match(db, make_chunk):
    """Рассинхрон текста и вектора — самая опасная ошибка: она не ломает
    поиск, а тихо портит его. Должна падать сразу и громко.
    """
    settings = make_settings()
    reset_index(db)
    document_id = insert_document(
        db,
        DocumentRow(
            slug="Web/Test",
            title="Тест",
            source_url="https://example.invalid",
            area="web/javascript",
            cyrillic_ratio=0.8,
            char_count=10,
        ),
    )

    with pytest.raises(ValueError, match="чужой вектор"):
        insert_chunks(db, document_id, [make_chunk(0, "текст")], [[0.1] * settings.embedding_dim] * 2)


@pytest.mark.db
def test_reindexing_same_document_does_not_duplicate(db, make_chunk):
    """Повторная индексация должна обновлять, а не плодить копии."""
    settings = make_settings()
    reset_index(db)
    row = DocumentRow(
        slug="Web/Test",
        title="Тест",
        source_url="https://example.invalid",
        area="web/javascript",
        cyrillic_ratio=0.8,
        char_count=10,
    )
    vectors = [[0.1] * settings.embedding_dim]

    for _ in range(2):
        document_id = insert_document(db, row)
        insert_chunks(db, document_id, [make_chunk(0, "текст")], vectors)

    assert count_rows(db) == (1, 1)


@pytest.mark.db
def test_cosine_distance_ranks_closer_vector_first(db, make_chunk):
    """Проверка, что векторный поиск в базе действительно работает."""
    settings = make_settings()
    reset_index(db)
    document_id = insert_document(
        db,
        DocumentRow(
            slug="Web/Test",
            title="Тест",
            source_url="https://example.invalid",
            area="web/javascript",
            cyrillic_ratio=0.8,
            char_count=10,
        ),
    )

    near = [1.0] + [0.0] * (settings.embedding_dim - 1)
    far = [0.0, 1.0] + [0.0] * (settings.embedding_dim - 2)
    insert_chunks(db, document_id, [make_chunk(0, "близкий"), make_chunk(1, "далёкий")], [near, far])

    with db.cursor() as cur:
        cur.execute(
            "SELECT content FROM chunks ORDER BY embedding <=> %s::vector LIMIT 1",
            (str(near),),
        )
        closest = cur.fetchone()[0]

    assert closest == "близкий"
