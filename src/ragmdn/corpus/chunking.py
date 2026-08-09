"""Нарезка разобранных документов на фрагменты для поиска.

Фрагмент — единица, которая ищется и попадает в ответ. Требования к нему
противоречат друг другу: достаточно большой, чтобы отвечать на вопрос
самостоятельно, и достаточно маленький, чтобы влезть в модель эмбеддингов
и не тащить в ответ лишнее.

Замеры по корпусу (8242 раздела) показали, что резать надо **в обе стороны**:

* медиана раздела — 254 символа, то есть большинство разделов сами по себе
  меньше желаемого фрагмента и их надо **склеивать**;
* 688 разделов короче 30 символов («Тип ошибки» с единственным словом
  `TypeError`) — как отдельная единица поиска бессмысленны;
* самый длинный раздел — 70 327 символов (справочник HTML-элементов),
  его надо **резать**.

Три правила, которые нельзя нарушать:

1. **Блок кода не разрывается.** Половина примера бесполезна читателю
   и ядовита для эмбеддинга.
2. **Фрагмент не состоит из одного кода.** Раздел «Синтаксис» у
   `Array.prototype.filter()` — только пример вызова; без окружающего текста
   он не найдётся ни по одному осмысленному вопросу.
3. **К фрагменту приписан путь заголовков.** Без него «Возвращает новый
   массив» неотличимо от десятка таких же фрагментов соседних страниц
   справочника — а таких страниц в MDN очень много.
"""

import re
from dataclasses import dataclass

from ragmdn.config import Settings
from ragmdn.corpus.parser import ParsedDocument, Section

_FENCED_CODE_BLOCK = re.compile(r"^[ \t]*```.*?^[ \t]*```", re.DOTALL | re.MULTILINE)
#: Граница предложения: точка/восклицательный/вопросительный знак, пробел,
#: заглавная буква. Сокращения вроде «т. е.» ломают эвристику, но она
#: применяется только к абзацам длиннее 1200 символов — там цена ошибки мала.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[А-ЯЁA-Z])")


@dataclass(frozen=True)
class Chunk:
    """Фрагмент документа — то, что кладётся в базу и ищется."""

    slug: str
    title: str
    source_url: str
    heading_path: tuple[str, ...]
    ordinal: int
    text: str

    @property
    def heading_line(self) -> str:
        return " › ".join(self.heading_path)

    @property
    def embedding_input(self) -> str:
        """Текст, который реально уходит в модель эмбеддингов.

        Путь заголовков приписан сверху: именно он отличает
        «Array.prototype.filter() › Описание» от
        «Array.prototype.map() › Описание» при почти одинаковом тексте.
        """
        return f"{self.heading_line}\n\n{self.text}"


def _is_code_block(block: str) -> bool:
    return block.lstrip().startswith("```")


def _split_into_blocks(text: str) -> list[str]:
    """Разбивает текст раздела на неделимые блоки: код и абзацы."""
    blocks: list[str] = []
    position = 0

    for match in _FENCED_CODE_BLOCK.finditer(text):
        before = text[position : match.start()]
        blocks.extend(p.strip() for p in before.split("\n\n") if p.strip())
        blocks.append(match.group(0).strip())
        position = match.end()

    tail = text[position:]
    blocks.extend(p.strip() for p in tail.split("\n\n") if p.strip())
    return blocks


def _split_text_units(units: list[str], separator: str, limit: int) -> list[str]:
    pieces: list[str] = []
    current = ""

    for unit in units:
        if not current:
            current = unit
        elif len(current) + len(separator) + len(unit) <= limit:
            current = f"{current}{separator}{unit}"
        else:
            pieces.append(current)
            current = unit

        while len(current) > limit:
            pieces.append(current[:limit])
            current = current[limit:]

    if current:
        pieces.append(current)
    return pieces


def _split_code_block(block: str, limit: int) -> list[str]:
    """Режет слишком длинный блок кода по строкам.

    Каждый кусок заново оборачивается в ограждения с тем же языком:
    без этого куски получаются с непарными ` ``` `, и дальше по конвейеру
    текст выглядит как сломанный markdown, а половина примера — как проза.
    """
    lines = block.strip().splitlines()
    opening = lines[0] if lines else "```"
    body = lines[1:]
    if body and body[-1].strip().startswith("```"):
        body = body[:-1]

    # Бюджет на содержимое: за вычетом ограждений и двух переводов строки.
    budget = max(limit - len(opening) - len("```") - 2, 1)
    return [
        f"{opening}\n{piece}\n```"
        for piece in _split_text_units(body, "\n", budget)
    ]


def _split_oversized_block(block: str, limit: int) -> list[str]:
    """Режет блок, который сам по себе не влезает в лимит.

    Обычный текст режется по границам предложений, а если и одно
    предложение длиннее лимита (встречается в справочных таблицах) —
    по символам. Код режется по строкам, с сохранением ограждений.
    """
    if len(block) <= limit:
        return [block]

    if _is_code_block(block):
        return _split_code_block(block, limit)

    return _split_text_units(_SENTENCE_BOUNDARY.split(block), " ", limit)


def _pack(blocks: list[str], target: int, limit: int) -> list[str]:
    """Жадно складывает блоки во фрагменты, не разрывая блоки."""
    packed: list[str] = []
    current: list[str] = []
    current_length = 0

    for block in blocks:
        for piece in _split_oversized_block(block, limit):
            piece_length = len(piece)
            if current and current_length + piece_length + 2 > target:
                packed.append("\n\n".join(current))
                current, current_length = [], 0
            current.append(piece)
            current_length += piece_length + 2

    if current:
        packed.append("\n\n".join(current))
    return packed


def _common_prefix(left: tuple[str, ...], right: tuple[str, ...]) -> tuple[str, ...]:
    prefix: list[str] = []
    for a, b in zip(left, right):
        if a != b:
            break
        prefix.append(a)
    return tuple(prefix)


def _heading_overhead(path: tuple[str, ...]) -> int:
    """Сколько символов добавит путь заголовков к тексту фрагмента.

    Лимит модели тратится на весь `embedding_input`, а не только на текст,
    поэтому бюджет на текст всегда уменьшается на эту величину.
    """
    return len(" › ".join(path)) + 2


def _merge_short_and_code_only(
    pieces: list[tuple[tuple[str, ...], str]], settings: Settings
) -> list[tuple[tuple[str, ...], str]]:
    """Склеивает слишком короткие фрагменты и фрагменты из одного кода.

    Склейка идёт только с **предыдущим** фрагментом того же документа и
    только если результат не превысит потолок: лучше оставить короткий
    фрагмент, чем получить фрагмент, который модель обрежет молча.
    """
    merged: list[tuple[tuple[str, ...], str]] = []

    for path, text in pieces:
        needs_company = len(text) < settings.chunk_min_chars or _is_code_block(text)

        if needs_company and merged:
            previous_path, previous_text = merged[-1]
            combined = f"{previous_text}\n\n{text}"
            combined_path = _common_prefix(previous_path, path) or previous_path
            if len(combined) + _heading_overhead(combined_path) <= settings.chunk_max_chars:
                merged[-1] = (combined_path, combined)
                continue

        merged.append((path, text))

    # Второй проход, справа налево: фрагмент из одного кода мог не влезть
    # в предыдущий, но помещается в следующий — например, когда до него шёл
    # длинный текст, а после идёт короткое пояснение.
    result: list[tuple[tuple[str, ...], str]] = []
    for path, text in reversed(merged):
        if _is_code_block(text) and result:
            next_path, next_text = result[-1]
            combined = f"{text}\n\n{next_text}"
            combined_path = _common_prefix(path, next_path) or next_path
            if len(combined) + _heading_overhead(combined_path) <= settings.chunk_max_chars:
                result[-1] = (combined_path, combined)
                continue
        result.append((path, text))

    result.reverse()
    return result


def _close_dangling_fence(text: str) -> str:
    """Гарантирует парность ограждений кода во фрагменте.

    Разметка в исходных файлах местами нестандартна — например, вложенный
    пример markdown внутри примера кода сбивает разбор. Полагаться на её
    аккуратность нельзя, поэтому инвариант «во фрагменте нет висячего
    ограждения» обеспечивается явно, а не надеждой на данные.
    """
    if text.count("```") % 2 == 0:
        return text
    return f"{text}\n```"


def chunk_sections(sections: tuple[Section, ...], settings: Settings) -> list[tuple[tuple[str, ...], str]]:
    """Превращает разделы документа в пары (путь заголовков, текст фрагмента)."""
    pieces: list[tuple[tuple[str, ...], str]] = []

    for section in sections:
        blocks = _split_into_blocks(section.text)
        # Путь заголовков уходит в модель вместе с текстом и тратит тот же
        # лимит, поэтому бюджет на текст уменьшается на его длину.
        overhead = _heading_overhead(section.heading_path)
        limit = max(settings.chunk_max_chars - overhead, 100)
        target = max(settings.chunk_target_chars - overhead, 100)
        for text in _pack(blocks, target, limit):
            pieces.append((section.heading_path, text))

    merged = _merge_short_and_code_only(pieces, settings)

    # Пустые и чисто пробельные фрагменты в индексе не нужны: искать в них
    # нечего, а место и время на эмбеддинг они занимают.
    return [
        (path, _close_dangling_fence(text)) for path, text in merged if text.strip()
    ]


def chunk_document(document: ParsedDocument, settings: Settings) -> list[Chunk]:
    """Нарезает разобранный документ на фрагменты."""
    return [
        Chunk(
            slug=document.slug,
            title=document.title,
            source_url=document.source_url,
            heading_path=path,
            ordinal=ordinal,
            text=text,
        )
        for ordinal, (path, text) in enumerate(chunk_sections(document.sections, settings))
    ]
