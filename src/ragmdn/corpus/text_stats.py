"""Чистые функции для оценки качества одного документа MDN.

Ничего не читает с диска и не ходит в сеть — поэтому проверяется
обычными юнит-тестами, без сети и без реального корпуса.
"""

import re
from collections import Counter

_FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]*`")
#: MathML-формулы дублируют себя в TeX внутри <annotation>. Это не проза,
#: а машинное представление — вырезаем блок целиком, а не только тег.
_ANNOTATION_BLOCK = re.compile(r"<annotation\b[^>]*>.*?</annotation>", re.DOTALL)
#: Любой прочий HTML-тег (таблицы совместимости, встроенные live-примеры,
#: остаток MathML вроде <mrow>, <mi>, <mo>) — вырезаем только сам тег,
#: текст внутри него часто настоящая русская проза и должен остаться.
_HTML_TAG = re.compile(r"<[^>]+>")
#: Адрес markdown-ссылки `[текст](адрес)`. Сам адрес — не проза: домены
#: и пути в URL почти всегда на латинице и не имеют отношения к переводу.
#: Текст ссылки в квадратных скобках остаётся.
_LINK_TARGET = re.compile(r"\]\([^)]*\)")
_MACRO_NAME = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)")
_CYRILLIC = re.compile(r"[а-яёА-ЯЁ]")
_LATIN = re.compile(r"[a-zA-Z]")


def strip_markup(text: str) -> str:
    """Убирает код и разметку, оставляя обычную прозу.

    Код и HTML-теги почти всегда написаны латиницей (идентификаторы,
    имена тегов, синтаксис), поэтому если их не убрать — доля кириллицы
    в тексте занижается искусственно, а не из-за плохого перевода.

    В файлах MDN, помимо кода в тройных кавычках, попадается и сырой HTML:
    таблицы совместимости браузеров, встроенные «живые примеры»
    ({{EmbedLiveSample}}), формулы MathML в статьях про Math.*, а также
    адреса в markdown-ссылках вида `[текст](адрес)` — сам адрес нередко
    содержит несколько английских слов из домена или пути, никак не
    связанных с качеством перевода статьи. Без этой очистки статья
    с отличным переводом получает заниженную оценку только из-за обвязки
    вокруг текста.
    """
    without_fences = _FENCED_CODE.sub(" ", text)
    without_inline_code = _INLINE_CODE.sub(" ", without_fences)
    without_annotations = _ANNOTATION_BLOCK.sub(" ", without_inline_code)
    without_tags = _HTML_TAG.sub(" ", without_annotations)
    return _LINK_TARGET.sub("]", without_tags)


def cyrillic_ratio(prose: str) -> float:
    """Доля кириллических букв среди всех кириллических и латинских.

    0.0 — текст полностью на латинице (перевода фактически нет),
    1.0 — текст полностью на кириллице. Документы без единой буквы
    (например, пустая строка) дают 0.0 — это не переведённый текст,
    это отсутствие текста, и его тоже не стоит индексировать.
    """
    cyrillic_count = len(_CYRILLIC.findall(prose))
    latin_count = len(_LATIN.findall(prose))
    total = cyrillic_count + latin_count
    if total == 0:
        return 0.0
    return cyrillic_count / total


def extract_macro_names(text: str) -> Counter[str]:
    """Считает, какие макросы MDN вида `{{JSRef}}` встречаются и сколько раз.

    Нужно, чтобы на шаге очистки текста не пропустить незнакомый макрос:
    список найденных имён сверяем с тем, что парсер умеет разворачивать.
    """
    return Counter(_MACRO_NAME.findall(text))


def is_stub(body: str, min_chars: int) -> bool:
    """Документ-заглушка: файл есть, а содержания в нём почти нет."""
    return len(body.strip()) < min_chars
