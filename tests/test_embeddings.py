"""Тесты слоя эмбеддингов.

Настоящая модель (2.24 ГБ, требует сети при первой загрузке) сюда не
подключается — это сделало бы обычный `pytest` медленным и зависимым от
интернета. Вместо неё — поддельный бэкенд, который просто запоминает,
какой текст ему передали. Реальная модель проверяется отдельным скриптом
(`embeddings_check.py`), уже на настоящих данных.
"""

from collections.abc import Iterable, Sequence

import pytest

from ragmdn.config import Settings
from ragmdn.embeddings import DimensionMismatchError, Embedder


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


class RecordingBackend:
    """Запоминает, какие строки ему передали, и возвращает вектор из нулей
    той длины, что задана в настройках — этого достаточно, чтобы проверить
    логику префиксов и склейки результатов, не считая ничего по-настоящему.
    """

    def __init__(self, dim: int):
        self.dim = dim
        self.received: list[str] = []

    def embed(self, texts: Iterable[str]) -> Iterable[Sequence[float]]:
        texts = list(texts)
        self.received.extend(texts)
        return [[0.0] * self.dim for _ in texts]


def test_passage_text_gets_passage_prefix():
    settings = make_settings()
    backend = RecordingBackend(settings.embedding_dim)
    embedder = Embedder(settings, backend)

    embedder.embed_passages(["Метод создаёт новый массив."])

    assert backend.received == ["passage: Метод создаёт новый массив."]


def test_query_text_gets_query_prefix():
    settings = make_settings()
    backend = RecordingBackend(settings.embedding_dim)
    embedder = Embedder(settings, backend)

    embedder.embed_query("Как отфильтровать массив?")

    assert backend.received == ["query: Как отфильтровать массив?"]


def test_identical_text_gets_different_prefix_depending_on_role():
    """Главная защита от путаницы: один и тот же текст как вопрос и как
    документ должен уйти в модель с разными префиксами — иначе не имеет
    смысла их вообще различать.
    """
    settings = make_settings()
    backend = RecordingBackend(settings.embedding_dim)
    embedder = Embedder(settings, backend)

    embedder.embed_query("filter")
    embedder.embed_passages(["filter"])

    assert backend.received == ["query: filter", "passage: filter"]


def test_embed_passages_preserves_order_and_count():
    settings = make_settings()
    backend = RecordingBackend(settings.embedding_dim)
    embedder = Embedder(settings, backend)

    vectors = embedder.embed_passages(["первый", "второй", "третий"])

    assert backend.received == ["passage: первый", "passage: второй", "passage: третий"]
    assert len(vectors) == 3


def test_embed_passages_of_empty_list_does_not_call_backend():
    settings = make_settings()
    backend = RecordingBackend(settings.embedding_dim)
    embedder = Embedder(settings, backend)

    assert embedder.embed_passages([]) == []
    assert backend.received == []


def test_dimension_mismatch_is_reported_loudly():
    """Регрессия ровно на ту находку, из-за которой пришлось поменять модель:
    если настройки разойдутся с реальной моделью, об этом нельзя молчать.
    """
    settings = make_settings()
    backend = RecordingBackend(dim=settings.embedding_dim - 1)  # намеренно неверная длина
    embedder = Embedder(settings, backend)

    with pytest.raises(DimensionMismatchError):
        embedder.embed_query("тест")


def test_query_vector_has_configured_dimension():
    settings = make_settings()
    embedder = Embedder(settings, RecordingBackend(settings.embedding_dim))

    vector = embedder.embed_query("тест")

    assert len(vector) == settings.embedding_dim
