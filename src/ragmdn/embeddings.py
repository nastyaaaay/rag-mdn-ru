"""Вычисление эмбеддингов.

Модель семейства E5 (и наша `intfloat/multilingual-e5-large` тоже) обучена
асимметрично: текст, который ищут («запрос»), и текст, который находят
(«документ»), должны кодироваться с разными префиксами — `query: ` и
`passage: `. Если это перепутать или забыть, модель не выдаст ошибку —
она просто посчитает векторы похуже, и качество поиска молча просядет.
Ошибку такого рода нельзя увидеть глазами на одном примере, только измерить.

Чтобы её нельзя было допустить по невнимательности, вызывающий код вообще
не видит сырой текст без префикса: `embed_passages` и `embed_query` —
единственный способ получить вектор, и оба сами решают, какой префикс нужен.
"""

from collections.abc import Iterable, Sequence
from typing import Protocol

from ragmdn.config import Settings

_QUERY_PREFIX = "query: "
_PASSAGE_PREFIX = "passage: "


class EmbeddingBackend(Protocol):
    """То, что реально считает векторы. В проде — обёртка над fastembed."""

    def embed(self, texts: Iterable[str]) -> Iterable[Sequence[float]]: ...


class DimensionMismatchError(RuntimeError):
    """Модель вернула вектор не той длины, что задана в настройках.

    Означает, что конфигурация разошлась с реальной моделью — например,
    поменяли `embedding_model`, не поправив `embedding_dim`. Молчать
    здесь нельзя: фрагмент с вектором неправильной длины либо не ляжет
    в базу, либо, если pgvector это не проверит, испортит поиск незаметно.
    """


class FastEmbedBackend:
    """Настоящий бэкенд поверх библиотеки fastembed.

    Загружает модель при первом обращении, а не при создании объекта:
    создание `Embedder` не должно требовать сети и модели, если код
    только собирается вызвать `embed_passages`, но ещё не вызвал.
    """

    def __init__(self, model_name: str):
        self._model_name = model_name
        self._model = None

    def embed(self, texts: Iterable[str]) -> Iterable[Sequence[float]]:
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self._model_name)
        return self._model.embed(list(texts))


class Embedder:
    """Единственная точка входа для получения эмбеддингов в проекте."""

    def __init__(self, settings: Settings, backend: EmbeddingBackend | None = None):
        self._settings = settings
        self._backend = backend or FastEmbedBackend(settings.embedding_model)

    def _check_dimension(self, vector: Sequence[float]) -> list[float]:
        if len(vector) != self._settings.embedding_dim:
            raise DimensionMismatchError(
                f"модель '{self._settings.embedding_model}' вернула вектор "
                f"длиной {len(vector)}, а в настройках embedding_dim={self._settings.embedding_dim}. "
                "Похоже, конфигурация не соответствует реальной модели."
            )
        return list(vector)

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        """Векторы для текста, который кладётся в индекс (фрагменты документов)."""
        if not texts:
            return []
        prefixed = [_PASSAGE_PREFIX + text for text in texts]
        return [self._check_dimension(vector) for vector in self._backend.embed(prefixed)]

    def embed_query(self, text: str) -> list[float]:
        """Вектор для пользовательского вопроса — при поиске по индексу."""
        vectors = list(self._backend.embed([_QUERY_PREFIX + text]))
        return self._check_dimension(vectors[0])
