"""Тесты конфигурации.

Настройки читаются без файла `.env`, иначе тесты зависели бы от того,
что лежит на конкретной машине, и падали бы у другого человека.
"""

import pytest

from ragmdn.config import PROJECT_ROOT, Settings


def make_settings(**overrides) -> Settings:
    """Настройки в изоляции от .env текущей машины."""
    return Settings(_env_file=None, **overrides)


def test_defaults_are_sane():
    settings = make_settings()

    assert settings.embedding_dim == 1024, "размерность должна совпадать с моделью e5-large"
    assert settings.llm_temperature == 0.0, "оценка качества требует воспроизводимых ответов"
    assert "web/javascript" in settings.mdn_areas


def test_web_api_is_excluded_from_corpus():
    """Web API исключён сознательно: его русский перевод отсутствует.

    Если кто-то вернёт его в список разделов, не поправив PLAN.md и README,
    этот тест напомнит, что решение было осознанным.
    """
    settings = make_settings()

    assert not any(area.startswith("web/api") for area in settings.mdn_areas)


def test_paths_stay_inside_project():
    settings = make_settings()

    assert settings.raw_dir == settings.data_dir / "raw"
    assert settings.data_dir.is_relative_to(PROJECT_ROOT)
    assert settings.reports_dir.is_relative_to(PROJECT_ROOT)


def test_environment_overrides_defaults(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "llama3.1:8b")
    monkeypatch.setenv("MIN_CYRILLIC_RATIO", "0.7")

    settings = make_settings()

    assert settings.llm_model == "llama3.1:8b"
    assert settings.min_cyrillic_ratio == 0.7


@pytest.mark.parametrize("bad_ratio", [-0.1, 1.5, 42.0])
def test_ratio_outside_range_is_rejected(bad_ratio):
    """Опечатка вида 50 вместо 0.5 должна падать громко, а не тихо всё отсеять."""
    with pytest.raises(ValueError):
        make_settings(min_cyrillic_ratio=bad_ratio)


def test_no_real_api_key_in_defaults():
    """Страж от случайно закоммиченного ключа.

    Значение по умолчанию — заглушка для локальной Ollama, которая ключи
    не проверяет. Настоящий ключ начинается с sk- и в коде оказаться не должен.
    """
    settings = make_settings()

    assert not settings.llm_api_key.startswith("sk-")
