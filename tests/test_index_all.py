"""Тесты индексации.

Индексация всего корпуса занимает минуты и требует базы — как тест она
не годится. Поэтому здесь проверяется логика на маленьком искусственном
корпусе из пары файлов, а полный прогон остаётся отдельной командой.
"""

from collections.abc import Iterable, Sequence

import pytest

from ragmdn.config import Settings
from ragmdn.corpus.report import build_report
from ragmdn.db import connect, count_rows, read_index_parameters
from ragmdn.embeddings import Embedder
from ragmdn.index_all import _collect_chunks, index_corpus

DOCUMENT = """\
---
title: Array.prototype.filter()
slug: Web/JavaScript/Reference/Global_Objects/Array/filter
---

{{JSRef}}

Метод **`filter()`** создаёт новый массив со всеми элементами, прошедшими
проверку, задаваемую в передаваемой функции. Это довольно длинное описание,
чтобы фрагмент получился содержательным и не был отброшен как слишком короткий.

## Описание

Метод вызывает переданную функцию один раз для каждого элемента массива.
Элементы, не прошедшие проверку, в новый массив не попадают.
"""

BROKEN_DOCUMENT = "заголовка нет, значит документ разобрать не получится\n"


def make_settings(tmp_path, database_url: str | None = None, **overrides) -> Settings:
    """Настройки для теста.

    `database_url` обязательно берётся из тестовой фикстуры там, где тест
    пишет в базу: индексация очищает таблицы, и на рабочей базе это стёрло бы
    результат часовой индексации.
    """
    if database_url is not None:
        overrides["database_url"] = database_url
    return Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        mdn_areas=("web/javascript",),
        **overrides,
    )


class FakeBackend:
    """Возвращает вектор нужной длины, ничего не вычисляя."""

    def __init__(self, dim: int):
        self.dim = dim
        self.calls = 0

    def embed(self, texts: Iterable[str]) -> Iterable[Sequence[float]]:
        texts = list(texts)
        self.calls += 1
        return [[0.01 * (i + 1)] * self.dim for i, _ in enumerate(texts)]


@pytest.fixture
def corpus(tmp_path):
    """Маленький корпус из двух документов: один хороший, один битый."""
    root = tmp_path / "ru"
    area = root / "web" / "javascript"
    (area / "filter").mkdir(parents=True)
    (area / "filter" / "index.md").write_text(DOCUMENT, encoding="utf-8")
    (area / "broken").mkdir(parents=True)
    (area / "broken" / "index.md").write_text(BROKEN_DOCUMENT, encoding="utf-8")
    return root


def test_collect_chunks_prepares_good_document(corpus, tmp_path):
    settings = make_settings(tmp_path)
    report = build_report(corpus, settings)

    prepared, failures = _collect_chunks(corpus, report, settings)

    assert len(prepared) == 1, "хороший документ должен быть разобран"
    assert prepared[0][1], "у документа должны быть фрагменты"
    assert failures == [], "на этом этапе битых документов уже не остаётся"


def test_broken_document_is_rejected_at_selection(corpus, tmp_path):
    """Документ без YAML-заголовка отсеивается ещё при отборе.

    До нарезки он не доходит, поэтому его причина попадает в отчёт отбора,
    а не в ошибки разбора. Проверяем именно там, где он реально отсеивается.
    """
    settings = make_settings(tmp_path)

    report = build_report(corpus, settings)

    assert len(report.errors) == 1
    assert "broken" in report.errors[0].relative_path
    assert report.errors[0].reason, "у пропуска должна быть внятная причина"


def test_failures_are_never_silent(corpus, tmp_path):
    """Ни один пропущенный документ не должен исчезнуть без следа.

    Отчёт индексации обязан собрать причины со всех этапов — и отбора,
    и разбора, — иначе часть корпуса тихо не доедет до базы.
    """
    settings = make_settings(tmp_path)
    report = build_report(corpus, settings)
    _, parse_failures = _collect_chunks(corpus, report, settings)

    all_failures = [(e.relative_path, e.reason) for e in report.errors] + parse_failures

    assert all_failures, "пропущенные документы должны быть перечислены"
    assert all(reason for _, reason in all_failures), "у каждого пропуска должна быть причина"


@pytest.mark.db
def test_index_corpus_writes_documents_and_chunks(corpus, tmp_path, database_available, test_settings):
    if database_available is not None:
        pytest.skip(f"база недоступна ({database_available})")

    settings = make_settings(tmp_path, test_settings.database_url)
    embedder = Embedder(settings, FakeBackend(settings.embedding_dim))

    report = index_corpus(corpus, settings, embedder)

    assert report.documents_indexed == 1
    assert report.chunks_indexed > 0
    assert len(report.failures) == 1  # битый документ

    with connect(settings) as conn:
        documents, chunks = count_rows(conn)
        assert documents == 1
        assert chunks == report.chunks_indexed


@pytest.mark.db
def test_index_corpus_records_parameters(corpus, tmp_path, database_available, test_settings):
    """После индексации в базе должны остаться параметры, которыми она сделана."""
    if database_available is not None:
        pytest.skip(f"база недоступна ({database_available})")

    settings = make_settings(tmp_path, test_settings.database_url)
    index_corpus(corpus, settings, Embedder(settings, FakeBackend(settings.embedding_dim)))

    with connect(settings) as conn:
        stored = read_index_parameters(conn)

    assert stored["embedding_model"] == settings.embedding_model
    assert stored["embedding_dim"] == str(settings.embedding_dim)


@pytest.mark.db
def test_reindexing_replaces_instead_of_accumulating(corpus, tmp_path, database_available, test_settings):
    if database_available is not None:
        pytest.skip(f"база недоступна ({database_available})")

    settings = make_settings(tmp_path, test_settings.database_url)
    embedder = Embedder(settings, FakeBackend(settings.embedding_dim))

    first = index_corpus(corpus, settings, embedder)
    second = index_corpus(corpus, settings, embedder)

    assert first.chunks_indexed == second.chunks_indexed

    with connect(settings) as conn:
        documents, chunks = count_rows(conn)

    assert documents == 1
    assert chunks == second.chunks_indexed
