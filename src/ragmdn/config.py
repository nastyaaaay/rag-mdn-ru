"""Настройки проекта.

Все значения берутся из переменных окружения или из файла `.env` в корне проекта.
В коде нет ни одного секрета — образец настроек лежит в `.env.example`.

Значения по умолчанию подобраны так, чтобы проект запускался сразу после
`docker compose up`, без правки конфигурации и без платных ключей.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Корень проекта: этот файл лежит в src/ragmdn/, поднимаемся на два уровня вверх.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Конфигурация приложения, собранная из окружения."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Корпус документов -------------------------------------------------

    mdn_repo: str = "mdn/translated-content"
    mdn_branch: str = "main"

    #: Разделы MDN, которые индексируем. Web API исключён сознательно:
    #: его русский перевод фактически отсутствует (замеры — в PLAN.md).
    mdn_areas: tuple[str, ...] = (
        "web/javascript",
        "web/css",
        "web/html",
        "web/http",
        "glossary",
    )

    #: Порог доли кириллицы в прозе. Документы ниже порога считаем
    #: непереведёнными и не индексируем. Значение уточняется на шаге 2
    #: по реальному распределению, а не на глаз.
    min_cyrillic_ratio: float = 0.5

    #: Документы короче этого считаем заглушками.
    min_document_chars: int = 200

    # --- Пути --------------------------------------------------------------

    data_dir: Path = PROJECT_ROOT / "data"

    # --- Нарезка на фрагменты ----------------------------------------------
    # Размеры заданы в символах, а не в токенах: подсчёт токенов требует
    # загрузки модели, а нарезка должна работать и без неё. Пересчёт грубый:
    # для русского текста примерно 2.5 символа на токен, и модель
    # multilingual-e5-small принимает не больше 512 токенов — всё сверх
    # обрезается молча, без ошибки. Отсюда потолок: 1200 символов текста
    # плюс путь заголовков укладываются в лимит с запасом.
    # Реальная проверка токенизатором — на шаге 6, вместе с эмбеддингами.

    chunk_target_chars: int = 800
    chunk_max_chars: int = 1200
    #: Ниже этого фрагмент склеивается с соседним: 688 разделов корпуса
    #: короче 30 символов («Тип ошибки: TypeError»), по отдельности они
    #: бесполезны как единица поиска.
    chunk_min_chars: int = 200

    # --- Эмбеддинги --------------------------------------------------------
    # multilingual-e5-small в библиотеке fastembed не зашит — она конвертирует
    # в ONNX не весь HuggingFace, а свой список моделей. Из этого списка
    # для русского языка подходит e5-large: та же схема с префиксами
    # query:/passage:, только крупнее (2.24 ГБ, 1024 измерения вместо 384).

    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_dim: int = 1024
    #: Предел модели. Вынесен в настройки, чтобы тест мог его проверить.
    embedding_max_tokens: int = 512

    # --- База данных -------------------------------------------------------

    database_url: str = "postgresql://rag:rag@localhost:5432/ragmdn"
    #: Секунды на попытку подключения. Без ограничения обращение к
    #: неподнятой базе висит очень долго вместо внятной ошибки.
    db_connect_timeout: int = 5

    # --- Языковая модель ---------------------------------------------------
    # Слой генерации говорит на OpenAI-совместимом протоколе. По умолчанию это
    # локальная Ollama, но те же настройки уводят запросы в любое облако.

    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"  # Ollama ключ не проверяет, но клиент требует непустой
    llm_model: str = "qwen2.5:7b-instruct"
    llm_temperature: float = 0.0  # нужен воспроизводимый ответ, а не разнообразный

    @property
    def raw_dir(self) -> Path:
        """Куда складываем скачанный корпус."""
        return self.data_dir / "raw"

    @property
    def reports_dir(self) -> Path:
        """Куда складываем отчёты о качестве."""
        return PROJECT_ROOT / "reports"

    @field_validator("min_cyrillic_ratio")
    @classmethod
    def _validate_ratio(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"min_cyrillic_ratio должен быть в диапазоне от 0 до 1, получено {value}"
            )
        return value

    @field_validator("embedding_dim")
    @classmethod
    def _validate_dim(cls, value: int) -> int:
        if value <= 0:
            raise ValueError(f"embedding_dim должен быть положительным, получено {value}")
        return value


@lru_cache
def get_settings() -> Settings:
    """Настройки читаются один раз за процесс."""
    return Settings()
