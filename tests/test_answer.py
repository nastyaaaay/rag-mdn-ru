"""Тесты сборки ответа.

Настоящая модель здесь не вызывается: она медленная, недетерминированная
и требует поднятого сервера. Проверяется то, что можно проверить точно —
промпт, разбор ссылок на источники и признаки выдумывания.
"""

import pytest

from ragmdn.answer import (
    NO_ANSWER,
    Answer,
    answer_question,
    build_messages,
    extract_citations,
    format_context,
)
from ragmdn.config import Settings
from ragmdn.llm import Message
from ragmdn.search import SearchHit


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def hit(slug: str, content: str, heading: str = "Заголовок › Раздел") -> SearchHit:
    return SearchHit(
        chunk_id=1,
        slug=slug,
        title=slug.rsplit("/", 1)[-1],
        source_url=f"https://developer.mozilla.org/ru/docs/{slug}",
        heading_path=heading,
        content=content,
        score=0.9,
    )


class ScriptedModel:
    """Отдаёт заранее заданный ответ и запоминает, что ей передали."""

    def __init__(self, reply: str):
        self.reply = reply
        self.received: list[Message] = []

    def complete(self, messages: list[Message]) -> str:
        self.received = messages
        return self.reply


# --- Промпт ---------------------------------------------------------------


def test_system_prompt_forbids_outside_knowledge():
    messages = build_messages("вопрос", [hit("A", "текст")])
    system = messages[0].content

    assert "ТОЛЬКО" in system
    assert NO_ANSWER in system


def test_context_is_numbered_for_citations():
    context = format_context([hit("A", "первый текст"), hit("B", "второй текст")])

    assert context.startswith("[1]")
    assert "[2]" in context
    assert "первый текст" in context
    assert "второй текст" in context


def test_context_includes_heading_path():
    """Без заголовка модель не отличит описание filter от описания map."""
    context = format_context([hit("A", "Метод создаёт новый массив.", "filter() › Описание")])

    assert "filter() › Описание" in context


def test_question_reaches_the_model():
    model = ScriptedModel("ответ")

    answer_question(model, "Как отфильтровать массив?", [hit("A", "текст")])

    assert "Как отфильтровать массив?" in model.received[1].content


# --- Разбор ссылок --------------------------------------------------------


def test_extracts_single_citation():
    assert extract_citations("Метод создаёт массив [1].") == (1,)


def test_extracts_multiple_citations_in_order():
    assert extract_citations("Сначала [2], потом [1].") == (2, 1)


def test_extracts_grouped_citations():
    assert extract_citations("Это верно [1, 3].") == (1, 3)


def test_ignores_repeated_citations():
    assert extract_citations("[1] и снова [1].") == (1,)


def test_no_citations_in_plain_text():
    assert extract_citations("Просто текст без ссылок.") == ()


# --- Ответ ----------------------------------------------------------------


def test_sources_map_to_actual_hits():
    hits = [hit("A", "первый"), hit("B", "второй")]
    model = ScriptedModel("Утверждение из второго фрагмента [2].")

    answer = answer_question(model, "вопрос", hits)

    assert answer.cited == (2,)
    assert answer.source_urls == ("https://developer.mozilla.org/ru/docs/B",)


def test_refusal_is_recognized():
    model = ScriptedModel(NO_ANSWER)

    answer = answer_question(model, "вопрос", [hit("A", "текст")])

    assert answer.is_refusal
    assert answer.source_urls == ()


def test_normal_answer_is_not_a_refusal():
    model = ScriptedModel("Метод создаёт новый массив [1].")

    answer = answer_question(model, "вопрос", [hit("A", "текст")])

    assert not answer.is_refusal


def test_citation_out_of_range_is_flagged():
    """Ссылка на несуществующий фрагмент — признак выдумывания.

    Это видно без всякой модели-судьи: номера больше, чем передано
    фрагментов, взяться неоткуда.
    """
    model = ScriptedModel("Так написано в документации [7].")

    answer = answer_question(model, "вопрос", [hit("A", "текст")])

    assert answer.has_invalid_citation
    assert answer.source_urls == ()


def test_valid_citations_are_not_flagged():
    model = ScriptedModel("Верно [1] и [2].")

    answer = answer_question(model, "вопрос", [hit("A", "раз"), hit("B", "два")])

    assert not answer.has_invalid_citation


def test_empty_search_result_skips_the_model_entirely():
    """Спрашивать модель не о чем — любой ответ был бы выдумкой."""
    model = ScriptedModel("я бы что-нибудь придумала")

    answer = answer_question(model, "вопрос", [])

    assert answer.is_refusal
    assert answer.text == NO_ANSWER
    assert model.received == [], "модель не должна вызываться без единого фрагмента"


def test_context_size_is_limited_by_settings():
    settings = make_settings(answer_context_chunks=2)
    hits = [hit(str(i), f"текст {i}") for i in range(5)]
    model = ScriptedModel("ответ [1].")

    answer = answer_question(model, "вопрос", hits, settings)

    assert len(answer.hits) == 2
    assert "текст 2" not in model.received[1].content


def test_duplicate_sources_are_collapsed():
    same = hit("A", "текст")
    model = ScriptedModel("Утверждение [1] и ещё одно [2].")

    answer = Answer(
        question="вопрос",
        text=model.reply,
        hits=(same, same),
        cited=extract_citations(model.reply),
    )

    assert answer.source_urls == ("https://developer.mozilla.org/ru/docs/A",)
