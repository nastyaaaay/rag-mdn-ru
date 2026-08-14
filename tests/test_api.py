"""Тесты HTTP-API.

Ни база, ни языковая модель здесь не нужны: поиск и модель подменяются.
Проверяется то, за что отвечает сам слой API — коды ответов, форма JSON
и то, что признаки выдумывания доходят до клиента, а не теряются по пути.
"""

import pytest
from fastapi.testclient import TestClient

from ragmdn import api
from ragmdn.answer import NO_ANSWER
from ragmdn.config import Settings
from ragmdn.llm import LLMError, Message
from ragmdn.search import SearchHit


def hit(slug: str = "Web/Test", content: str = "текст фрагмента") -> SearchHit:
    return SearchHit(
        chunk_id=1,
        slug=slug,
        title="Тест",
        source_url=f"https://developer.mozilla.org/ru/docs/{slug}",
        heading_path="Тест › Раздел",
        content=content,
        score=0.87,
    )


class ScriptedModel:
    def __init__(self, reply: str | Exception):
        self.reply = reply

    def complete(self, messages: list[Message]) -> str:
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


@pytest.fixture
def client(monkeypatch):
    """Клиент API с подменёнными поиском, базой и моделью."""
    settings = Settings(_env_file=None)

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(api, "connect", lambda *a, **k: FakeConnection())
    monkeypatch.setattr(api, "search", lambda *a, **k: [hit()])
    monkeypatch.setattr(api, "count_rows", lambda conn: (1323, 7895))

    api._state["settings"] = settings
    api._state["embedder"] = object()
    api._state["model"] = ScriptedModel("Метод создаёт новый массив [1].")

    with TestClient(api.app) as test_client:
        # TestClient запускает lifespan и перетирает подмены — возвращаем их
        api._state["model"] = ScriptedModel("Метод создаёт новый массив [1].")
        api._state["embedder"] = object()
        yield test_client

    api._state.clear()


def test_health_reports_index_size(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["chunks"] == 7895
    assert response.json()["documents"] == 1323


def test_ask_returns_answer_with_sources(client):
    response = client.post("/ask", json={"question": "Что возвращает filter?"})

    assert response.status_code == 200
    data = response.json()
    assert "новый массив" in data["answer"]
    assert data["is_refusal"] is False
    assert data["sources"][0]["url"].startswith("https://developer.mozilla.org/")


def test_ask_marks_refusal(client):
    api._state["model"] = ScriptedModel(NO_ANSWER)

    data = client.post("/ask", json={"question": "чем useState отличается от useEffect"}).json()

    assert data["is_refusal"] is True
    assert data["sources"] == []


def test_ask_reports_invented_citation(client):
    """Признак выдумывания обязан доходить до клиента, а не теряться."""
    api._state["model"] = ScriptedModel("Так написано в документации [9].")

    data = client.post("/ask", json={"question": "вопрос про что-нибудь"}).json()

    assert data["has_invalid_citation"] is True
    assert data["sources"] == []


def test_ask_rejects_too_short_question(client):
    response = client.post("/ask", json={"question": "а"})

    assert response.status_code == 422


def test_ask_rejects_unknown_method(client):
    response = client.post("/ask", json={"question": "нормальный вопрос", "method": "телепатия"})

    assert response.status_code == 422


def test_unavailable_model_returns_503_not_500(client):
    """Недоступная модель — временный сбой снаружи, а не ошибка приложения."""
    api._state["model"] = ScriptedModel(LLMError("сервер не отвечает"))

    response = client.post("/ask", json={"question": "нормальный вопрос"})

    assert response.status_code == 503
    assert "модель недоступна" in response.json()["detail"]


def test_search_endpoint_does_not_call_the_model(client):
    """Поиск обязан работать, даже когда языковая модель недоступна."""
    api._state["model"] = ScriptedModel(LLMError("сервер не отвечает"))

    response = client.post("/search", json={"question": "как отфильтровать массив"})

    assert response.status_code == 200
    assert response.json()["hits"][0]["url"].startswith("https://developer.mozilla.org/")


def test_index_page_is_served(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Вопрос по документации MDN" in response.text
