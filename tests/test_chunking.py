"""Тесты нарезки на фрагменты."""

from ragmdn.config import Settings
from ragmdn.corpus.chunking import Chunk, chunk_document, chunk_sections
from ragmdn.corpus.parser import Section, parse_document


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def section(text: str, *path: str) -> Section:
    return Section(heading_path=path or ("Документ",), text=text)


def test_short_section_stays_whole():
    settings = make_settings()
    pieces = chunk_sections((section("Короткий, но осмысленный абзац. " * 10),), settings)

    assert len(pieces) == 1


def test_long_section_is_split():
    settings = make_settings()
    long_text = "\n\n".join(f"Абзац номер {i}. " * 20 for i in range(10))

    pieces = chunk_sections((section(long_text),), settings)

    assert len(pieces) > 1
    for _, text in pieces:
        assert len(text) <= settings.chunk_max_chars


def test_code_block_is_never_split_in_half():
    settings = make_settings()
    code = "```js\n" + "\n".join(f"const value{i} = {i};" for i in range(12)) + "\n```"
    text = f"Описание примера ниже. {'Пояснение. ' * 30}\n\n{code}"

    pieces = chunk_sections((section(text),), settings)

    joined = "\n\n".join(t for _, t in pieces)
    assert joined.count("```") % 2 == 0, "непарные ограждения — блок кода разорван"
    for _, piece in pieces:
        assert piece.count("```") % 2 == 0


def test_oversized_code_block_keeps_balanced_fences():
    """Регрессия: при резке длинного примера куски теряли ограждения,
    и по корпусу получался 151 фрагмент со сломанным markdown.
    """
    settings = make_settings()
    huge_code = "```js\n" + "\n".join(f"const value{i} = {i};" for i in range(200)) + "\n```"

    pieces = chunk_sections((section(huge_code),), settings)

    assert len(pieces) > 1
    for _, text in pieces:
        assert text.count("```") == 2, "у куска кода должны быть открывающее и закрывающее ограждение"
        assert text.strip().startswith("```js")
        assert text.strip().endswith("```")
        assert len(text) <= settings.chunk_max_chars


def test_code_only_fragment_may_attach_to_following_text():
    """Если слева длинный текст, код должен прилипнуть к тому, что справа."""
    settings = make_settings()
    sections = (
        section("Очень длинное вступление. " * 40, "Док", "Вступление"),
        section("```js\nfoo();\n```", "Док", "Синтаксис"),
        section("Короткое пояснение к примеру.", "Док", "Пояснение"),
    )

    pieces = chunk_sections(sections, settings)

    code_only = [t for _, t in pieces if t.strip().startswith("```") and t.count("```") == 2]
    assert code_only == [], "остался фрагмент из одного лишь кода"


def test_code_only_fragment_is_glued_to_neighbour():
    """Раздел «Синтаксис» у справочных страниц состоит только из кода."""
    settings = make_settings()
    sections = (
        section("Метод создаёт новый массив. " * 5, "filter()", "Описание"),
        section("```js\nfilter(callbackFn)\n```", "filter()", "Синтаксис"),
    )

    pieces = chunk_sections(sections, settings)

    for _, text in pieces:
        stripped = text.strip()
        assert not stripped.startswith("```") or "\n\n" in stripped, (
            "фрагмент состоит только из кода"
        )


def test_tiny_sections_are_merged():
    """688 разделов корпуса короче 30 символов — по отдельности бесполезны."""
    settings = make_settings()
    sections = (
        section("TypeError", "RangeError: radix", "Тип ошибки"),
        section("- Number.prototype.toString()", "RangeError: radix", "Смотрите также"),
    )

    pieces = chunk_sections(sections, settings)

    assert len(pieces) == 1
    assert "TypeError" in pieces[0][1]
    assert "toString()" in pieces[0][1]


def test_merged_pieces_keep_common_heading_prefix():
    settings = make_settings()
    sections = (
        section("TypeError", "Ошибка X", "Тип ошибки"),
        section("- ссылка", "Ошибка X", "Смотрите также"),
    )

    path, _ = chunk_sections(sections, settings)[0]

    assert path[0] == "Ошибка X"


def test_merge_never_exceeds_hard_limit():
    """Склейка коротких не должна создать фрагмент сверх потолка."""
    settings = make_settings()
    big = "Длинный связный текст. " * 50
    sections = (section(big, "Док", "Раздел"), section("TypeError", "Док", "Тип"))

    pieces = chunk_sections(sections, settings)

    for _, text in pieces:
        assert len(text) <= settings.chunk_max_chars


def test_single_oversized_paragraph_is_still_split():
    """Абзац без единой границы предложения тоже обязан влезть в лимит."""
    settings = make_settings()
    monster = "слово " * 800

    pieces = chunk_sections((section(monster),), settings)

    assert len(pieces) > 1
    for _, text in pieces:
        assert len(text) <= settings.chunk_max_chars


def test_embedding_input_respects_limit_including_heading():
    """Лимит модели тратится на весь embedding_input, а не только на текст.

    Путь заголовков в справочнике MDN бывает длинным
    («Array.prototype.filter() › Примеры › Фильтрация записей JSON»),
    и без учёта его длины самые большие фрагменты молча обрезались бы
    моделью — без ошибки и без единого признака в логе.
    """
    settings = make_settings()
    long_path = (
        "Array.prototype.filter()",
        "Примеры использования метода",
        "Фильтрация неверных записей в JSON-объекте",
    )
    text = "\n\n".join(f"Содержательный абзац номер {i}. " * 12 for i in range(8))

    pieces = chunk_sections((section(text, *long_path),), settings)

    for path, piece in pieces:
        full_length = len(" › ".join(path)) + 2 + len(piece)
        assert full_length <= settings.chunk_max_chars


def test_code_heavy_chunk_is_smaller_than_prose_chunk():
    """Регрессия на измерение: код расходует лимит модели вдвое быстрее прозы.

    В корпусе нашёлся фрагмент с примером кода (шахматная доска массивом
    строк): 1102 символа дали 617 токенов при лимите 512 — модель отрезала бы
    хвост молча. Проза даёт около 3.6 символа на токен, плотный код — 1.8,
    поэтому код считается с двойным весом и такие фрагменты режутся раньше.
    """
    settings = make_settings()
    code_line = '  ["R", "N", "B", "Q", "K", "B", "N", "R"],'
    code = "```js\nconst board = [\n" + "\n".join([code_line] * 40) + "\n];\n```"

    pieces = chunk_sections((section(code),), settings)

    for _, text in pieces:
        # С двойным весом фрагмент кода не должен занимать весь лимит символов
        assert len(text) <= settings.chunk_max_chars // 2 + 200


def test_chunk_embedding_input_starts_with_heading_path():
    chunk = Chunk(
        slug="Web/JavaScript/Reference/Global_Objects/Array/filter",
        title="Array.prototype.filter()",
        source_url="https://developer.mozilla.org/ru/docs/Web/JS/filter",
        heading_path=("Array.prototype.filter()", "Описание"),
        ordinal=0,
        text="Метод создаёт новый массив.",
    )

    assert chunk.embedding_input.startswith("Array.prototype.filter() › Описание")
    assert "Метод создаёт новый массив." in chunk.embedding_input


def test_chunk_document_numbers_fragments_in_order():
    settings = make_settings()
    raw = """\
---
title: Пример
slug: Web/Test
---

## Первый

Текст первого раздела, достаточно длинный для отдельного фрагмента. Ещё текст.

## Второй

Текст второго раздела, тоже вполне самостоятельный и осмысленный. И ещё.
"""
    chunks = chunk_document(parse_document(raw), settings)

    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert all(c.slug == "Web/Test" for c in chunks)
    assert all(c.source_url.endswith("Web/Test") for c in chunks)


def test_empty_document_yields_no_chunks():
    settings = make_settings()

    assert chunk_sections((), settings) == []


def test_whitespace_only_section_is_dropped():
    """В корпусе нашёлся фрагмент из одних пробелов — искать в нём нечего."""
    settings = make_settings()

    assert chunk_sections((section("   \n\n   \t  "),), settings) == []


def test_dangling_fence_is_closed():
    """Разметка в исходниках местами нестандартна; инвариант обеспечиваем сами."""
    settings = make_settings()
    broken = "Пояснение к примеру ниже, достаточно длинное. ```js\nfoo();"

    pieces = chunk_sections((section(broken),), settings)

    for _, text in pieces:
        assert text.count("```") % 2 == 0
