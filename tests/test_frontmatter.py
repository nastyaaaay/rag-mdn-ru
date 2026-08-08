import pytest

from ragmdn.corpus.frontmatter import FrontmatterError, split_frontmatter


def test_splits_title_and_slug():
    raw = (
        "---\n"
        "title: Array.prototype.map()\n"
        "slug: Web/JavaScript/Reference/Global_Objects/Array/map\n"
        "---\n"
        "\n"
        "## Сводка\n"
        "Метод создаёт новый массив.\n"
    )

    fields, body = split_frontmatter(raw)

    assert fields["title"] == "Array.prototype.map()"
    assert fields["slug"] == "Web/JavaScript/Reference/Global_Objects/Array/map"
    assert "## Сводка" in body
    assert "---" not in body


def test_strips_surrounding_quotes():
    raw = '---\ntitle: "Значение в кавычках"\nslug: Test\n---\nТело.\n'

    fields, _ = split_frontmatter(raw)

    assert fields["title"] == "Значение в кавычках"


def test_ignores_unrecognized_multiline_fields():
    """Поля вроде browser-compat нам не нужны — не должны ронять парсер."""
    raw = (
        "---\n"
        "title: Пример\n"
        "slug: Test\n"
        "browser-compat: javascript.builtins.Array.map\n"
        "---\n"
        "Тело документа.\n"
    )

    fields, body = split_frontmatter(raw)

    assert fields["title"] == "Пример"
    assert "Тело документа." in body


def test_missing_frontmatter_raises():
    with pytest.raises(FrontmatterError):
        split_frontmatter("Просто текст без заголовка.\n")


def test_unterminated_frontmatter_raises():
    with pytest.raises(FrontmatterError):
        split_frontmatter("---\ntitle: Без закрытия\nТело сразу.\n")
