"""Превращение файла MDN в чистый текст с метаданными.

Порядок обработки важен и выбран не случайно:

1. Блоки кода прячутся под заглушки. Всё остальное — разворачивание макросов,
   чистка HTML, склейка списков — не должно трогать содержимое примеров кода:
   в примере `<div>` это код, который читателю нужен, а в тексте статьи это
   разметка, которую надо убрать. Различить их можно только так.
2. Разворачиваются макросы MDN (см. `macros.py`).
3. Разворачиваются блоки-врезки `> [!NOTE]`.
4. Склеиваются списки определений — в MDN так описаны параметры функций.
5. Убираются HTML-теги, текст внутри них остаётся.
6. Блоки кода возвращаются на место.

Результат — документ, разложенный по разделам, у каждого известен путь
из заголовков. Этот путь потом приписывается к фрагменту перед вычислением
эмбеддинга: без него фрагмент «Возвращает новый массив» неотличим от десятка
таких же фрагментов из соседних страниц справочника.
"""

import re
from collections import Counter
from dataclasses import dataclass

from ragmdn.corpus.frontmatter import split_frontmatter
from ragmdn.corpus.macros import expand_macros

MDN_BASE_URL = "https://developer.mozilla.org/ru/docs/"

#: Маркер спрятанного блока кода. Символ \x00 в текстах не встречается.
_CODE_PLACEHOLDER = "\x00CODE{index}\x00"
_PLACEHOLDER_PATTERN = re.compile(r"\x00CODE(\d+)\x00")

_FENCED_CODE = re.compile(r"^[ \t]*```.*?^[ \t]*```", re.DOTALL | re.MULTILINE)
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_CALLOUT_START = re.compile(r"^>\s*\[!(NOTE|WARNING|CALLOUT)\]\s*$", re.IGNORECASE)
_QUOTED_LINE = re.compile(r"^>\s?(.*)$")
#: Строка-определение из списка параметров MDN: `  - : описание`.
_DEFINITION_LINE = re.compile(r"^\s*-\s*:\s*(.*)$")
_LIST_ITEM = re.compile(r"^(\s*)[-*]\s+(.*)$")
_HTML_TAG = re.compile(r"</?[A-Za-z][^>]*>")
_MULTIPLE_BLANK_LINES = re.compile(r"\n{3,}")
#: Markdown-ссылка `[текст](адрес)` и картинка `![описание](адрес)`.
#: Адрес в скобках может сам содержать скобки — например, ссылки на
#: Википедию вида `Ajax_(программирование)`, — поэтому один уровень
#: вложенности разрешён явно.
_MARKDOWN_LINK = re.compile(r"!?\[([^\]]*)\]\((?:[^()]|\([^()]*\))*\)")

_CALLOUT_LABELS = {
    "NOTE": "Примечание.",
    "WARNING": "Предупреждение.",
    "CALLOUT": "",
}


class ParseError(ValueError):
    """Документ невозможно разобрать — не хватает обязательных метаданных."""


@dataclass(frozen=True)
class Section:
    """Раздел документа: путь из заголовков и текст под ними."""

    heading_path: tuple[str, ...]
    text: str

    @property
    def heading_line(self) -> str:
        """Путь в виде строки — приписывается к фрагменту перед эмбеддингом."""
        return " › ".join(self.heading_path)


@dataclass(frozen=True)
class ParsedDocument:
    slug: str
    title: str
    source_url: str
    sections: tuple[Section, ...]
    unknown_macros: Counter[str]

    @property
    def text(self) -> str:
        return "\n\n".join(section.text for section in self.sections)


def _hide_code_blocks(text: str) -> tuple[str, list[str]]:
    blocks: list[str] = []

    def stash(match: re.Match[str]) -> str:
        blocks.append(match.group(0))
        return _CODE_PLACEHOLDER.format(index=len(blocks) - 1)

    return _FENCED_CODE.sub(stash, text), blocks


def _restore_code_blocks(text: str, blocks: list[str]) -> str:
    def unstash(match: re.Match[str]) -> str:
        return blocks[int(match.group(1))]

    return _PLACEHOLDER_PATTERN.sub(unstash, text)


def _unwrap_callouts(text: str) -> str:
    """Разворачивает врезки `> [!NOTE]` в обычные абзацы.

    Сама плашка заменяется словом «Примечание» или «Предупреждение»:
    для поиска важно, что это оговорка, а не основное утверждение.
    """
    lines = text.splitlines()
    result: list[str] = []
    index = 0

    while index < len(lines):
        start = _CALLOUT_START.match(lines[index])
        if start is None:
            result.append(lines[index])
            index += 1
            continue

        label = _CALLOUT_LABELS[start.group(1).upper()]
        index += 1
        body: list[str] = []
        while index < len(lines):
            quoted = _QUOTED_LINE.match(lines[index])
            if quoted is None:
                break
            body.append(quoted.group(1))
            index += 1

        paragraph = " ".join(part.strip() for part in body if part.strip())
        result.append(f"{label} {paragraph}".strip() if label else paragraph)

    return "\n".join(result)


def _flatten_definition_lists(text: str) -> str:
    """Склеивает термин и его определение в одну строку.

    В MDN параметры функций записаны так::

        - `callbackFn`
          - : Функция, вызываемая для каждого элемента.

    Читателю это показывается как список определений, но в виде плоского
    текста две строки выглядят как несвязанные пункты списка. Склеиваем
    их в «`callbackFn` — Функция, вызываемая для каждого элемента.»
    """
    lines = text.splitlines()
    result: list[str] = []

    for line in lines:
        definition = _DEFINITION_LINE.match(line)
        if definition is None:
            result.append(line)
            continue

        body = definition.group(1).strip()
        # Ищем последний непустой пункт списка — это термин.
        for position in range(len(result) - 1, -1, -1):
            if not result[position].strip():
                continue
            if _LIST_ITEM.match(result[position]):
                result[position] = f"{result[position].rstrip()} — {body}"
                break
            result.append(body)
            break
        else:
            result.append(body)

    return "\n".join(result)


def _split_sections(text: str, root_title: str) -> tuple[Section, ...]:
    """Разбивает текст по заголовкам, запоминая путь до каждого раздела."""
    sections: list[Section] = []
    # heading_stack[i] — заголовок уровня i+1
    heading_stack: list[str] = [root_title]
    buffer: list[str] = []

    def flush() -> None:
        body = _MULTIPLE_BLANK_LINES.sub("\n\n", "\n".join(buffer)).strip()
        if body:
            sections.append(Section(heading_path=tuple(heading_stack), text=body))
        buffer.clear()

    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading is None:
            buffer.append(line)
            continue

        flush()
        level = len(heading.group(1))
        title = heading.group(2).strip()
        # Уровень 1 в файлах MDN не используется — заголовок берётся
        # из frontmatter, поэтому корень всегда остаётся на месте.
        depth = max(level - 1, 1)
        heading_stack = heading_stack[:depth]
        while len(heading_stack) < depth:
            heading_stack.append("")
        heading_stack.append(title)

    flush()
    return tuple(sections)


def parse_document(raw: str) -> ParsedDocument:
    """Разбирает содержимое одного файла `index.md`."""
    fields, body = split_frontmatter(raw)

    slug = fields.get("slug")
    if not slug:
        raise ParseError("в заголовке файла нет поля slug — неоткуда взять ссылку на источник")
    title = fields.get("title") or slug.rsplit("/", 1)[-1]

    hidden, code_blocks = _hide_code_blocks(body)
    expanded, unknown_macros = expand_macros(hidden)
    without_callouts = _unwrap_callouts(expanded)
    flattened = _flatten_definition_lists(without_callouts)
    without_html = _HTML_TAG.sub("", flattened)
    # Адрес ссылки — не текст: пути вроде /ru/docs/Learn_web_development/
    # Core/Scripting/Network_requests добавляют в фрагмент десяток английских
    # слов, которых читатель на странице не видит, и размывают эмбеддинг.
    without_link_targets = _MARKDOWN_LINK.sub(r"\1", without_html)
    restored = _restore_code_blocks(without_link_targets, code_blocks)

    sections = _split_sections(restored, title)

    return ParsedDocument(
        slug=slug,
        title=title,
        source_url=MDN_BASE_URL + slug,
        sections=sections,
        unknown_macros=unknown_macros,
    )
