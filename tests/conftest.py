"""Общие фикстуры для всех тестов.

Файл с таким именем pytest подхватывает автоматически, и объявленные здесь
фикстуры видны во всех тестовых модулях.

**Тесты работают с отдельной базой, а не с рабочей.** Это не педантизм:
тесты очищают таблицы перед проверкой, и на рабочей базе один прогон
`pytest` стирал результат часовой индексации. Проверено на себе.
Имя тестовой базы — рабочее с суффиксом `_test`, она создаётся
автоматически при первом запуске.
"""

import re

import psycopg
import pytest
from psycopg import sql

from ragmdn.config import PROJECT_ROOT, Settings
from ragmdn.db import connect

SCHEMA_PATH = PROJECT_ROOT / "db" / "init" / "01-schema.sql"


def _test_database_url(url: str) -> str:
    """Тот же сервер, но база с суффиксом _test."""
    return re.sub(r"/([^/?]+)(\?|$)", r"/\1_test\2", url)


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Настройки, указывающие на тестовую базу."""
    base = Settings(_env_file=None)
    return Settings(_env_file=None, database_url=_test_database_url(base.database_url))


@pytest.fixture(scope="session")
def database_available(test_settings) -> str | None:
    """Готовит тестовую базу. Возвращает None при успехе, иначе текст ошибки.

    Создаётся один раз за прогон: подключаемся к служебной базе `postgres`,
    создаём тестовую, если её нет, и накатываем ту же схему, что и у рабочей.
    """
    admin_url = re.sub(r"/([^/?]+)(\?|$)", r"/postgres\2", Settings(_env_file=None).database_url)
    target = re.search(r"/([^/?]+)(\?|$)", test_settings.database_url).group(1)

    try:
        with psycopg.connect(admin_url, connect_timeout=3, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target,))
                if cur.fetchone() is None:
                    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target)))

        with connect(test_settings, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.chunks')")
                if cur.fetchone()[0] is None:
                    cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))

        return None
    except Exception as exc:  # noqa: BLE001 — годится любая неудача подключения
        return str(exc)
