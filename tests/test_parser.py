"""Тесты парсера документов MDN."""

import pytest

from ragmdn.corpus.parser import ParseError, parse_document

ARRAY_FILTER = """\
---
title: Array.prototype.filter()
slug: Web/JavaScript/Reference/Global_Objects/Array/filter
---

{{JSRef}}

Метод **`filter()`** создаёт новый массив.

### Параметры

- `callbackFn`
  - : Функция-предикат, вызываемая для каждого элемента.
- `thisArg`{{optional_inline}}
  - : Значение, используемое как `this`.

### Возвращаемое значение

Новый массив с элементами, прошедшими проверку.

## Спецификации

{{Specifications}}
"""


def test_extracts_metadata_and_builds_source_url():
    doc = parse_document(ARRAY_FILTER)

    assert doc.title == "Array.prototype.filter()"
    assert doc.slug == "Web/JavaScript/Reference/Global_Objects/Array/filter"
    assert doc.source_url == (
        "https://developer.mozilla.org/ru/docs/"
        "Web/JavaScript/Reference/Global_Objects/Array/filter"
    )


def test_definition_list_is_glued_into_one_line():
    doc = parse_document(ARRAY_FILTER)

    assert "`callbackFn` — Функция-предикат, вызываемая для каждого элемента." in doc.text


def test_inline_label_survives_into_definition():
    doc = parse_document(ARRAY_FILTER)

    assert "`thisArg` (необязательный) — Значение, используемое как `this`." in doc.text


def test_widget_macros_leave_no_trace():
    doc = parse_document(ARRAY_FILTER)

    assert "JSRef" not in doc.text
    assert "Specifications" not in doc.text


def test_heading_path_tracks_nesting():
    doc = parse_document(ARRAY_FILTER)
    paths = [section.heading_path for section in doc.sections]

    assert ("Array.prototype.filter()",) in paths
    assert ("Array.prototype.filter()", "", "Параметры") in paths


def test_heading_line_is_human_readable():
    doc = parse_document(ARRAY_FILTER)
    lines = [section.heading_line for section in doc.sections]

    assert any("Array.prototype.filter()" in line and "Параметры" in line for line in lines)


def test_missing_slug_raises():
    with pytest.raises(ParseError):
        parse_document("---\ntitle: Без slug\n---\nТекст.\n")


def test_code_block_content_is_preserved_verbatim():
    """HTML внутри примера кода — это код, а не разметка статьи."""
    raw = """\
---
title: Пример
slug: Web/Test
---

Разметка страницы <em>выделяется</em> так:

```html
<div class="wrapper">
  <span>Привет</span>
</div>
```
"""
    doc = parse_document(raw)

    assert '<div class="wrapper">' in doc.text
    assert "<span>Привет</span>" in doc.text
    # А вот тег в обычном тексте убран, слово внутри осталось
    assert "<em>" not in doc.text
    assert "выделяется" in doc.text


def test_macros_inside_code_blocks_are_not_expanded():
    raw = """\
---
title: Шаблоны
slug: Web/Test
---

```js
const tpl = `{{ user.name }}`;
```
"""
    doc = parse_document(raw)

    assert "{{ user.name }}" in doc.text


def test_note_callout_becomes_plain_paragraph():
    raw = """\
---
title: Пример
slug: Web/Test
---

> [!NOTE]
> Отрицательные значения недопустимы.
> Значение приводится к числу.
"""
    doc = parse_document(raw)

    assert "Примечание." in doc.text
    assert "Отрицательные значения недопустимы. Значение приводится к числу." in doc.text
    assert ">" not in doc.text


def test_warning_callout_is_labelled_differently():
    raw = """\
---
title: Пример
slug: Web/Test
---

> [!WARNING]
> Метод изменяет исходный массив.
"""
    doc = parse_document(raw)

    assert "Предупреждение." in doc.text


def test_reference_macro_keeps_russian_word_in_sentence():
    """Регрессия на находку из корпуса: подпись ссылки бывает русской."""
    raw = """\
---
title: Доступность
slug: Glossary/Accessibility
---

Речь идёт о {{Glossary("computer programming", "программировании")}} интерфейсов.
"""
    doc = parse_document(raw)

    assert "о программировании интерфейсов" in doc.text
    assert "computer programming" not in doc.text


def test_document_without_headings_still_yields_one_section():
    raw = """\
---
title: Короткая заметка
slug: Glossary/Short
---

Одно предложение без единого заголовка.
"""
    doc = parse_document(raw)

    assert len(doc.sections) == 1
    assert doc.sections[0].heading_path == ("Короткая заметка",)


def test_markdown_link_keeps_text_and_drops_target():
    raw = """\
---
title: Пример
slug: Web/Test
---

Подробнее в [Service Worker API](/ru/docs/Web/API/Service_Worker_API).
"""
    doc = parse_document(raw)

    assert "Подробнее в Service Worker API." in doc.text
    assert "/ru/docs/" not in doc.text


def test_markdown_link_target_may_contain_parentheses():
    """Ссылки на Википедию вида Ajax_(программирование) не должны рвать разбор."""
    raw = """\
---
title: Пример
slug: Web/Test
---

Смотрите [AJAX](https://ru.wikipedia.org/wiki/Ajax_(программирование)) в Википедии.
"""
    doc = parse_document(raw)

    assert "Смотрите AJAX в Википедии." in doc.text
    assert "wikipedia.org" not in doc.text


def test_image_is_replaced_by_its_description():
    raw = """\
---
title: Пример
slug: Web/Test
---

![Схема блочной модели](box-model.png)
"""
    doc = parse_document(raw)

    assert "Схема блочной модели" in doc.text
    assert "box-model.png" not in doc.text


def test_links_inside_code_blocks_are_untouched():
    raw = """\
---
title: Пример
slug: Web/Test
---

```js
// см. [документацию](https://example.com/docs)
const url = "https://example.com/docs";
```
"""
    doc = parse_document(raw)

    assert "[документацию](https://example.com/docs)" in doc.text
    assert 'const url = "https://example.com/docs";' in doc.text


def test_unknown_macros_are_collected_not_swallowed():
    raw = """\
---
title: Пример
slug: Web/Test
---

Плашка {{TotallyNewMacro}} и ссылка {{AnotherNew("текст")}}.
"""
    doc = parse_document(raw)

    assert doc.unknown_macros["TotallyNewMacro"] == 1
    assert doc.unknown_macros["AnotherNew"] == 1
    assert "текст" in doc.text
