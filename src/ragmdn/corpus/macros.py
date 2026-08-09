"""Разворачивание макросов MDN.

Тексты MDN написаны не на чистом markdown: в них встроен шаблонизатор
KumaScript — вызовы вида `{{jsxref("Array")}}`. Всего в нашем корпусе
45 различных макросов, и обходиться с ними надо по-разному.

Три категории:

* **Ссылочные** несут видимый текст, который читатель видит на странице.
  Их нельзя удалять: `{{Glossary("computer programming", "программировании")}}`
  отображается как слово «программировании», и выбросив макрос, мы потеряли бы
  русское слово из предложения. Берётся **последний** строковый аргумент —
  в MDN это подпись ссылки, а первый аргумент лишь адрес цели.
* **Пометки** — короткие плашки у названия («экспериментальная возможность»,
  «только для чтения»). Заменяем русским текстом: это полезно для поиска,
  вопрос «какие свойства устарели» должен что-то находить.
* **Виджеты и навигация** (таблицы совместимости, боковые панели, встроенные
  примеры) на странице разворачиваются в интерактивные блоки, которых в тексте
  нет. Удаляем.

Незнакомый макрос не удаляется молча: он попадает в список неизвестных,
который печатается в сводке прогона.
"""

import re
from collections import Counter

#: Макрос целиком: имя и необязательные аргументы в скобках.
#: Внутри аргументов встречаются и скобки, и точки — `{{jsxref("Statements/if...else",
#: "if (condition)")}}` — поэтому содержимое забирается нежадно до первых `}}`,
#: а разбирается уже отдельным выражением.
_MACRO_CALL = re.compile(r"\{\{(.+?)\}\}", re.DOTALL)
_MACRO_HEAD = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*(?:\((.*)\))?\s*$", re.DOTALL)
#: Строковый аргумент в двойных или одинарных кавычках.
_STRING_ARG = re.compile(r'"([^"]*)"' r"|'([^']*)'")

#: Ссылочные макросы: берём последний строковый аргумент как видимый текст.
DISPLAY_MACROS = frozenset(
    {
        "jsxref",
        "cssxref",
        "htmlelement",
        "glossary",
        "httpheader",
        "domxref",
        "httpstatus",
        "httpmethod",
        "rfc",
        "svgelement",
        "svgattr",
        "mathmlelement",
        "csp",
    }
)

#: Пометки-плашки: заменяем русским текстом.
INLINE_LABELS = {
    "optional_inline": " (необязательный)",
    "experimental_inline": " (экспериментальная возможность)",
    "deprecated_inline": " (устаревшая возможность)",
    "non-standard_inline": " (нестандартная возможность)",
    "readonlyinline": " (только для чтения)",
    "securecontext_inline": " (требуется защищённый контекст)",
    "deprecated_header": "\n\nУстаревшая возможность: не рекомендуется к использованию.\n\n",
    "non-standard_header": "\n\nНестандартная возможность: поддерживается не всеми браузерами.\n\n",
    "seecompattable": "\n\nЭкспериментальная возможность: проверяйте совместимость с браузерами.\n\n",
}

#: Виджеты, таблицы и навигация — на странице разворачиваются в интерактивные
#: блоки, текстового содержания не несут.
DROP_MACROS = frozenset(
    {
        "compat",
        "specifications",
        "embedlivesample",
        "embedghlivesample",
        "interactiveexample",
        "jsfiddleembed",
        "jsref",
        "cssref",
        "css_ref",
        "htmlsidebar",
        "jssidebar",
        "glossarysidebar",
        "learnsidebar",
        "glossarydisambiguation",
        "csssyntax",
        "cssinfo",
        "js_property_attributes",
        "previousnext",
        "previousmenunext",
        "previous",
        "next",
        "quicklinkswithsubpages",
        "listsubpages",
    }
)


def _string_arguments(raw_args: str) -> list[str]:
    """Строковые аргументы вызова, в порядке появления."""
    return [
        double or single for double, single in _STRING_ARG.findall(raw_args)
    ]


def expand_macros(text: str) -> tuple[str, Counter[str]]:
    """Разворачивает макросы MDN в обычный текст.

    Возвращает очищенный текст и счётчик **неизвестных** макросов —
    тех, что не попали ни в одну из трёх категорий. Вызывающий код обязан
    показать их в сводке: молча выброшенный незнакомый макрос означает
    потерянный кусок текста, о котором никто не узнает.
    """
    unknown: Counter[str] = Counter()

    def replace(match: re.Match[str]) -> str:
        head = _MACRO_HEAD.match(match.group(1))
        if head is None:
            # Не похоже на вызов макроса — например, фрагмент кода
            # с двойными фигурными скобками. Оставляем как есть.
            return match.group(0)

        name, raw_args = head.group(1), head.group(2) or ""
        key = name.lower()

        if key in DROP_MACROS:
            return ""
        if key in INLINE_LABELS:
            return INLINE_LABELS[key]
        if key in DISPLAY_MACROS:
            args = _string_arguments(raw_args)
            # Последний строковый аргумент — подпись ссылки; если аргумент
            # один, он же и адрес, и подпись.
            return args[-1] if args else ""

        unknown[name] += 1
        # Неизвестный макрос: сохраняем текст аргумента, если он есть —
        # потерять слово хуже, чем оставить лишнее.
        args = _string_arguments(raw_args)
        return args[-1] if args else ""

    return _MACRO_CALL.sub(replace, text), unknown
