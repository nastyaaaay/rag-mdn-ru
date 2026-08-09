from ragmdn.corpus.text_stats import (
    cyrillic_ratio,
    extract_macro_names,
    is_stub,
    strip_markup,
)


def test_strip_markup_removes_fenced_blocks():
    text = "Текст до.\n```js\nconst x = 1;\n```\nТекст после."
    result = strip_markup(text)

    assert "const x" not in result
    assert "Текст до." in result
    assert "Текст после." in result


def test_strip_markup_removes_inline_code_only():
    text = "Вызовите метод `Array.prototype.map()` для каждого элемента."
    result = strip_markup(text)

    assert "Array.prototype.map()" not in result
    assert "для каждого элемента" in result


def test_strip_markup_does_not_eat_across_paragraphs():
    """Инлайн-код без закрывающего апострофа не должен съесть весь абзац."""
    text = "Первый абзац с `открытым код.\nВторой абзац — обычный текст."
    result = strip_markup(text)

    assert "Второй абзац" in result


def test_strip_markup_removes_html_tags_but_keeps_inner_text():
    """Таблицы совместимости и live-примеры — сырой HTML внутри markdown.

    Сами теги — разметка, а текст внутри ячейки часто настоящая русская проза.
    """
    text = "<table><tr><td>Поддерживается</td></tr></table>"
    result = strip_markup(text)

    assert "<td>" not in result
    assert "Поддерживается" in result


def test_strip_markup_removes_link_url_but_keeps_link_text():
    text = "Подробнее: [документация MDN](https://example.com/some-long-english-path)."
    result = strip_markup(text)

    assert "example.com" not in result
    assert "some-long-english-path" not in result
    assert "документация MDN" in result


def test_strip_markup_keeps_ordinary_parentheses():
    """Скобки как часть обычной русской фразы — не адрес ссылки, трогать нельзя."""
    text = "Метод возвращает арккосинус числа (в радианах)."
    result = strip_markup(text)

    assert "в радианах" in result


def test_strip_markup_removes_tex_annotation_block_entirely():
    """<annotation> внутри MathML дублирует формулу в TeX — не проза, а код.

    В отличие от обычных HTML-тегов, здесь вырезается и содержимое: LaTeX
    вроде \\operatorname{Math.acos} только зашумляет подсчёт латиницы.
    """
    text = (
        "Метод возвращает арккосинус."
        '<math><annotation encoding="TeX">\\operatorname{acos}(x)</annotation></math>'
    )
    result = strip_markup(text)

    assert "operatorname" not in result
    assert "Метод возвращает арккосинус." in result


def test_cyrillic_ratio_pure_russian():
    assert cyrillic_ratio("Метод создаёт новый массив") == 1.0


def test_cyrillic_ratio_pure_english():
    assert cyrillic_ratio("The method creates a new array") == 0.0


def test_cyrillic_ratio_mixed():
    # 2 кириллические буквы, 2 латинские -> ровно половина
    ratio = cyrillic_ratio("аб cd")
    assert ratio == 0.5


def test_cyrillic_ratio_no_letters_at_all():
    """Пустой или чисто символьный текст — не переведённый текст, а его отсутствие."""
    assert cyrillic_ratio("   123 --- ") == 0.0


def test_cyrillic_ratio_ignores_code_when_combined_with_strip_markup():
    text = "Русское описание метода.\n```js\nfunction identity(x) { return x; }\n```"
    ratio = cyrillic_ratio(strip_markup(text))

    assert ratio == 1.0


def test_cyrillic_ratio_of_glossary_entry_with_english_url_improves_after_strip():
    """Регрессионный тест на реальную находку: глоссарий про XMLHttpRequest
    переведён отлично, но ссылка на английскую статью
    (peoplesofttutorial.com/difference-between-synchronous-and-asynchronous...)
    добавляла восемь английских слов, которых нет в видимом тексте статьи.
    """
    text = (
        "XMLHttpRequest (XHR) это API для создания AJAX запросов.\n"
        "- Полезная информация о [XMLHttpRequest]"
        "(https://peoplesofttutorial.com/difference-between-synchronous-and-asynchronous-messaging/)\n"
        "- [Разница между синхронной и асинхронной передачи сообщений]"
        "(https://peoplesofttutorial.com/difference-between-synchronous-and-asynchronous-messaging/)"
    )

    ratio = cyrillic_ratio(strip_markup(text))

    assert ratio > 0.5


def test_cyrillic_ratio_of_well_translated_math_page_improves_after_strip():
    """Регрессионный тест на реальную находку: Math.acos() переведён отлично,
    но формула MathML с TeX-аннотацией занижала долю кириллицы до 40%.
    """
    text = (
        "Метод **`Math.acos()`** возвращает арккосинус числа."
        '<math display="block"><semantics><mrow><mo>∀</mo><mi>x</mi></mrow>'
        '<annotation encoding="TeX">\\forall x \\in [{-1};1]</annotation>'
        "</semantics></math>"
        "Метод вернёт NaN, если значение выйдет за этот диапазон."
    )

    ratio = cyrillic_ratio(strip_markup(text))

    assert ratio > 0.9


def test_extract_macro_names_finds_flags_and_calls():
    text = (
        "{{JSRef}}\n\n"
        "Значение по умолчанию — {{jsxref(\"undefined\")}}.\n"
        "Параметр{{optional_inline}} необязателен.\n"
        "Ещё раз: {{jsxref(\"Array\")}}."
    )
    macros = extract_macro_names(text)

    assert macros["JSRef"] == 1
    assert macros["jsxref"] == 2
    assert macros["optional_inline"] == 1


def test_extract_macro_names_keeps_hyphenated_names_intact():
    """Регрессия: имя обрезалось на дефисе, и в отчёте появлялся
    несуществующий макрос `{{non}}` вместо `{{non-standard_inline}}`.
    """
    text = "Свойство{{non-standard_inline}} нестандартное.{{non-standard_header}}"
    macros = extract_macro_names(text)

    assert macros["non-standard_inline"] == 1
    assert macros["non-standard_header"] == 1
    assert "non" not in macros


def test_extract_macro_names_empty_when_none_present():
    assert extract_macro_names("Обычный текст без макросов.") == {}


def test_is_stub_short_document():
    assert is_stub("Коротко.", min_chars=200) is True


def test_is_stub_long_document():
    body = "Достаточно длинный текст. " * 20
    assert is_stub(body, min_chars=200) is False


def test_is_stub_counts_stripped_whitespace():
    """Файл из одних переводов строк не должен притворяться содержательным."""
    assert is_stub("\n\n\n   \n\n", min_chars=1) is True
