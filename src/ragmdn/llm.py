"""Клиент языковой модели поверх OpenAI-совместимого протокола.

Протокол выбран не ради OpenAI: его понимают Ollama, OpenRouter, Groq,
GitHub Models и другие. Благодаря этому переключение поставщика — три
строки в `.env`, а код не меняется вовсе. По умолчанию работает локальная
модель, поэтому проект воспроизводится без ключей и без оплаты.

Модуль намеренно тонкий: он умеет отправить сообщения и вернуть текст.
Всё, что касается промпта и разбора ответа, живёт в `answer.py` — там
это можно проверить тестами, не поднимая никакой модели.
"""

from dataclasses import dataclass
from typing import Protocol

import httpx

from ragmdn.config import Settings


class LLMError(RuntimeError):
    """Модель недоступна или вернула неожиданный ответ."""


@dataclass(frozen=True)
class Message:
    role: str
    content: str


class ChatModel(Protocol):
    """То, что умеет отвечать на набор сообщений. В тестах подменяется."""

    def complete(self, messages: list[Message]) -> str: ...


class OpenAICompatibleModel:
    """Обращение к модели по протоколу /v1/chat/completions."""

    def __init__(self, settings: Settings, timeout: float | None = None):
        self._settings = settings
        # Локальная модель на процессоре отвечает медленно, и таймаут
        # по умолчанию у httpx (5 секунд) обрывал бы каждый запрос.
        self._timeout = timeout if timeout is not None else settings.llm_timeout

    def complete(self, messages: list[Message]) -> str:
        payload = {
            "model": self._settings.llm_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self._settings.llm_temperature,
        }
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self._settings.llm_api_key}",
        }

        try:
            response = httpx.post(
                f"{self._settings.llm_base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"модель ответила ошибкой {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(
                f"не удалось обратиться к модели по адресу {self._settings.llm_base_url}: {exc}"
            ) from exc

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"неожиданный формат ответа модели: {str(data)[:300]}") from exc
