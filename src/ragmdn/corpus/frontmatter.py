"""Разбор YAML-заголовка файлов MDN.

Заголовок в файлах MDN — плоский список `ключ: значение` между двумя
строками `---`. Настоящий YAML-парсер сюда ставить незачем: полноценный
YAML умеет вложенные структуры и многострочные значения, которых в
заголовках MDN не бывает — нужны только `title` и `slug`.
"""

import re

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?\n)---\s*\n(.*)\Z", re.DOTALL)
_FIELD = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")


class FrontmatterError(ValueError):
    """Файл не содержит распознаваемого заголовка MDN."""


def split_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """Возвращает (поля заголовка, тело документа без заголовка).

    Поднимает FrontmatterError, если файл не начинается с блока `---`.
    Вызывающий код обязан это поймать и посчитать как ошибку в сводке
    прогона — тихо пропускать такие файлы нельзя.
    """
    match = _FRONTMATTER.match(raw)
    if match is None:
        raise FrontmatterError("файл не начинается с YAML-заголовка `---`")

    header_block, body = match.groups()
    fields: dict[str, str] = {}
    for line in header_block.splitlines():
        field_match = _FIELD.match(line)
        if field_match is None:
            continue  # многострочные поля вроде browser-compat нам не нужны
        key, value = field_match.groups()
        fields[key] = value.strip().strip("'\"")

    return fields, body
