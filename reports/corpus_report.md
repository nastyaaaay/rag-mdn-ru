# Отчёт о качестве корпуса MDN

Найдено файлов: **1429**, успешно разобрано: **1429**, ошибок разбора: **0**.

При пороге доли кириллицы **50%**: включено в индекс **1323**, исключено как непереведённые **99**, исключено как заглушки **7**.

## Документов по разделам

| Раздел | Найдено | Включено при текущем пороге |
|---|---:|---:|
| `web/javascript` | 602 | 587 |
| `web/css` | 350 | 295 |
| `web/html` | 127 | 113 |
| `web/http` | 121 | 114 |
| `glossary` | 229 | 214 |

## Распределение доли кириллицы в прозе

Код и инлайн-код исключены из подсчёта — считается только обычный текст.

```
  0-10 % | █ 15
 10-20 % | █ 16
 20-30 % | █ 13
 30-40 % | ██ 25
 40-50 % | ██ 30
 50-60 % | █████ 66
 60-70 % | ██████████████ 182
 70-80 % | ███████████████████████████████ 396
 80-90 % | ████████████████████████████████████████ 505
 90-100% | ██████████████ 174
```

## Документы у границы порога (для ручной проверки)

Все документы, чья доля кириллицы попадает в диапазон [40%, 60%] — именно на этой границе фильтр может ошибиться в обе стороны.

| Доля кириллицы | Раздел | Путь |
|---:|---|---|
| 40% | `web/css` | `web/css/reference/properties/column-rule-color/index.md` |
| 41% | `web/css` | `web/css/guides/media_queries/index.md` |
| 41% | `web/css` | `web/css/how_to/layout_cookbook/index.md` |
| 41% | `web/css` | `web/css/reference/values/filter-function/invert/index.md` |
| 42% | `web/css` | `web/css/guides/syntax/introduction/index.md` |
| 42% | `web/javascript` | `web/javascript/reference/global_objects/symbol/replace/index.md` |
| 42% | `web/css` | `web/css/reference/properties/grid-row-start/index.md` |
| 42% | `web/javascript` | `web/javascript/reference/global_objects/symbol/split/index.md` |
| 42% | `web/css` | `web/css/reference/properties/border-bottom/index.md` |
| 42% | `web/css` | `web/css/reference/values/filter-function/blur/index.md` |
| 43% | `web/css` | `web/css/reference/at-rules/@font-feature-values/index.md` |
| 43% | `web/http` | `web/http/reference/headers/index.md` |
| 44% | `glossary` | `glossary/w3c/index.md` |
| 45% | `web/css` | `web/css/reference/properties/right/index.md` |
| 45% | `web/html` | `web/html/reference/elements/input/date/index.md` |
| 46% | `web/css` | `web/css/reference/selectors/_colon_lang/index.md` |
| 46% | `web/http` | `web/http/guides/content_negotiation/index.md` |
| 47% | `web/css` | `web/css/guides/fonts/index.md` |
| 47% | `web/javascript` | `web/javascript/reference/global_objects/symbol/search/index.md` |
| 48% | `web/css` | `web/css/reference/selectors/pseudo-classes/index.md` |
| 48% | `web/javascript` | `web/javascript/reference/errors/precision_range/index.md` |
| 48% | `web/javascript` | `web/javascript/reference/global_objects/generator/index.md` |
| 48% | `glossary` | `glossary/forbidden_response_header_name/index.md` |
| 48% | `web/javascript` | `web/javascript/reference/global_objects/weakmap/delete/index.md` |
| 48% | `web/css` | `web/css/reference/selectors/_doublecolon_first-letter/index.md` |
| ... | и ещё 71 документов | |

## Заглушки

Всего: 7 (короче 200 символов).

| Раздел | Путь | Символов |
|---|---|---:|
| `glossary` | `glossary/block/index.md` | 117 |
| `glossary` | `glossary/buffer/index.md` | 155 |
| `glossary` | `glossary/cia/index.md` | 175 |
| `glossary` | `glossary/privileged_code/index.md` | 197 |
| `glossary` | `glossary/property/index.md` | 148 |
| `glossary` | `glossary/safe/index.md` | 149 |
| `glossary` | `glossary/webp/index.md` | 195 |

## Макросы MDN

Всего различных макросов: 74.

| Макрос | Встречается раз |
|---|---:|
| `{{jsxref}}` | 4286 |
| `{{cssxref}}` | 2222 |
| `{{HTMLElement}}` | 1946 |
| `{{Compat}}` | 965 |
| `{{Specifications}}` | 912 |
| `{{Glossary}}` | 632 |
| `{{EmbedLiveSample}}` | 552 |
| `{{HTTPHeader}}` | 469 |
| `{{domxref}}` | 400 |
| `{{JSRef}}` | 397 |
| `{{Cssxref}}` | 379 |
| `{{glossary}}` | 372 |
| `{{CSSRef}}` | 332 |
| `{{InteractiveExample}}` | 309 |
| `{{GlossarySidebar}}` | 224 |
| `{{JSxRef}}` | 223 |
| `{{HTTPStatus}}` | 221 |
| `{{experimental_inline}}` | 200 |
| `{{csssyntax}}` | 189 |
| `{{jsSidebar}}` | 182 |
| `{{HTTPMethod}}` | 162 |
| `{{CSSxRef}}` | 150 |
| `{{cssinfo}}` | 139 |
| `{{HTMLSidebar}}` | 123 |
| `{{htmlelement}}` | 111 |
| `{{RFC}}` | 88 |
| `{{non}}` | 80 |
| `{{optional_inline}}` | 72 |
| `{{EmbedGHLiveSample}}` | 62 |
| `{{js_property_attributes}}` | 40 |
