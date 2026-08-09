"""Тесты разворачивания макросов MDN.

Почти все примеры взяты дословно из реального корпуса — искусственные
случаи здесь бесполезны, ошибки прячутся именно в настоящих данных.
"""

from ragmdn.corpus.macros import expand_macros


def test_reference_macro_with_single_argument_keeps_name():
    text, unknown = expand_macros('Значение по умолчанию — {{jsxref("undefined")}}.')

    assert text == "Значение по умолчанию — undefined."
    assert unknown == {}


def test_reference_macro_with_two_arguments_keeps_display_text():
    """Второй аргумент — подпись ссылки, первый лишь адрес."""
    text, _ = expand_macros('Смотрите {{jsxref("Functions/arguments","arguments")}}.')

    assert text == "Смотрите arguments."
    assert "Functions/arguments" not in text


def test_reference_macro_preserves_russian_display_text():
    """Ключевой случай: подпись ссылки бывает на русском.

    Если бы брался первый аргумент, из предложения пропало бы русское
    слово и его место занял бы английский адрес — и текст, и метрика
    доли кириллицы поехали бы.
    """
    text, _ = expand_macros(
        'Речь о {{Glossary("computer programming", "программировании")}}.'
    )

    assert text == "Речь о программировании."


def test_reference_macro_handles_single_quotes():
    text, _ = expand_macros("Заголовок {{HTTPHeader('Date')}} обязателен.")

    assert text == "Заголовок Date обязателен."


def test_reference_macro_survives_parentheses_inside_argument():
    """`if (condition)` внутри аргумента не должен обрывать разбор."""
    text, _ = expand_macros(
        'Оператор {{jsxref("Statements/if...else","if (condition)")}} ветвит код.'
    )

    assert text == "Оператор if (condition) ветвит код."


def test_reference_macro_survives_empty_call_parens_inside_argument():
    text, _ = expand_macros(
        '{{jsxref("RegExp/Symbol.replace", "RegExp.prototype[@@replace]()")}}'
    )

    assert text == "RegExp.prototype[@@replace]()"


def test_macro_name_is_case_insensitive():
    """В корпусе соседствуют {{glossary}}, {{Glossary}}, {{cssxref}}, {{Cssxref}}."""
    lower, _ = expand_macros('{{glossary("API")}}')
    upper, _ = expand_macros('{{Glossary("API")}}')

    assert lower == upper == "API"


def test_inline_label_becomes_russian_text():
    text, _ = expand_macros("- `thisArg`{{optional_inline}}")

    assert text == "- `thisArg` (необязательный)"


def test_hyphenated_label_is_recognized():
    text, _ = expand_macros("Свойство{{non-standard_inline}} работает не везде.")

    assert "нестандартная возможность" in text.lower()


def test_widget_macros_are_removed():
    text, unknown = expand_macros(
        "{{JSRef}}\n\n## Спецификации\n\n{{Specifications}}\n\n{{Compat}}"
    )

    assert "JSRef" not in text
    assert "Specifications" not in text
    assert "Compat" not in text
    assert "## Спецификации" in text
    assert unknown == {}


def test_widget_macro_with_arguments_is_removed_entirely():
    text, _ = expand_macros('Пример: {{EmbedLiveSample("Демо", 300, 200)}}')

    assert "Демо" not in text
    assert "300" not in text


def test_unknown_macro_is_reported_and_its_text_kept():
    """Незнакомый макрос не должен пропадать бесследно."""
    text, unknown = expand_macros('Ссылка {{SomeNewMacro("важное слово")}} здесь.')

    assert "важное слово" in text
    assert unknown["SomeNewMacro"] == 1


def test_unknown_macro_without_arguments_is_reported():
    text, unknown = expand_macros("Плашка {{BrandNewBadge}} тут.")

    assert unknown["BrandNewBadge"] == 1
    assert "BrandNewBadge" not in text


def test_double_braces_in_code_are_left_alone():
    """Шаблонный синтаксис в примерах кода — не макрос MDN."""
    source = "const tpl = `{{ user.name }}`;"
    text, unknown = expand_macros(source)

    assert unknown == {}


def test_real_symbol_replace_fragment():
    """Фрагмент из web/javascript/reference/global_objects/symbol/replace."""
    source = (
        "Эта функция вызывается методом {{jsxref(\"String.prototype.replace()\")}}.\n\n"
        "{{js_property_attributes(0,0,0)}}\n\n"
        "## Спецификации\n\n{{Specifications}}"
    )

    text, unknown = expand_macros(source)

    assert "String.prototype.replace()" in text
    assert "js_property_attributes" not in text
    assert "## Спецификации" in text
    assert unknown == {}
