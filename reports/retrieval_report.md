# Качество поиска

Метрики посчитаны без участия языковой модели: сопоставляются только найденные документы с эталонными. Цифры воспроизводимы — один и тот же индекс всегда даёт один и тот же результат.

**Recall@k** — доля вопросов, где нужный документ попал в первые k результатов. **MRR** — насколько высоко он оказался (1.0 значит «всегда первым»).

## Способ поиска: `vector`

| Группа вопросов | Вопросов | R@1 | R@3 | R@5 | R@10 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| cross | 5 | 60% | 80% | 80% | 80% | 0.700 |
| direct | 15 | 80% | 93% | 93% | 100% | 0.867 |
| natural | 12 | 8% | 42% | 50% | 67% | 0.263 |
| similar | 10 | 20% | 30% | 30% | 30% | 0.250 |
| ВСЕГО | 42 | 43% | 62% | 64% | 71% | 0.528 |

Не найдено вовсе: 12 вопросов — `n02`, `n04`, `n10`, `n12`, `s01`, `s02`, `s03`, `s05`, `s06`, `s07`, `s08`, `c04`

## Способ поиска: `vector_nocode`

| Группа вопросов | Вопросов | R@1 | R@3 | R@5 | R@10 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| cross | 5 | 60% | 80% | 80% | 80% | 0.700 |
| direct | 15 | 73% | 93% | 93% | 100% | 0.833 |
| natural | 12 | 8% | 50% | 58% | 58% | 0.281 |
| similar | 10 | 20% | 30% | 30% | 30% | 0.250 |
| ВСЕГО | 42 | 40% | 64% | 67% | 69% | 0.521 |

Не найдено вовсе: 13 вопросов — `n02`, `n04`, `n10`, `n11`, `n12`, `s01`, `s02`, `s03`, `s05`, `s06`, `s07`, `s08`, `c04`

## Вопросы, на которых система промахнулась

### `vector`

**n02** (natural): как из массива цен получить массив цен со скидкой

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/map`
- найдено: `Glossary/Array`, `Web/JavaScript/Reference/Global_Objects/Set`, `Web/JavaScript/Reference/Global_Objects/Object/values`, `Web/JavaScript/Reference/Global_Objects/Array/from`, `Web/JavaScript/Reference/Errors/Reduce_of_empty_array_with_no_initial_value`, `Web/JavaScript/Reference/Global_Objects/Array/slice`, `Web/JavaScript/Guide/Language_overview`, `Web/JavaScript/Reference/Global_Objects/Array/reduce`

**n04** (natural): пишу obj.user.name и падает ошибка если user нет

- ожидалось: `Web/JavaScript/Reference/Operators/Optional_chaining`
- найдено: `Web/JavaScript/Reference/Errors/Missing_name_after_dot_operator`, `Web/JavaScript/Reference/Global_Objects/ReferenceError`, `Web/JavaScript/Reference/Global_Objects/Symbol/unscopables`, `Web/JavaScript/Reference/Errors/Unnamed_function_statement`, `Web/JavaScript/Reference/Global_Objects/SyntaxError`, `Web/JavaScript/Reference/Global_Objects/Reflect/defineProperty`, `Web/JavaScript/Reference/Operators/Property_accessors`, `Web/JavaScript/Reference/Statements/throw`

**n10** (natural): объявил переменную в цикле, а снаружи её не видно, почему

- ожидалось: `Web/JavaScript/Reference/Statements/let`
- найдено: `Web/JavaScript/Guide/Grammar_and_types`, `Web/JavaScript/Reference/Statements/var`, `Web/JavaScript/Guide/Closures`, `Web/JavaScript/Reference/Statements/block`, `Web/JavaScript/Reference/Errors/Undeclared_var`, `Web/JavaScript/Guide/Language_overview`

**n12** (natural): хочу прижать элемент к низу экрана чтобы он не уезжал при прокрутке

- ожидалось: `Web/CSS/Reference/Properties/position`
- найдено: `Web/CSS/Reference/Properties/background-attachment`, `Web/CSS/Reference/Properties/overscroll-behavior`, `Web/CSS/Reference/Properties/scroll-snap-type`, `Web/CSS/Reference/At-rules/@media/prefers-reduced-motion`, `Web/CSS/Reference/Properties/scroll-behavior`, `Web/CSS/Reference/Properties/cursor`

**s01** (similar): какой метод массива возвращает новый массив той же длины

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/map`
- найдено: `Web/JavaScript/Reference/Global_Objects/Array/slice`, `Web/JavaScript/Reference/Global_Objects/Array/unshift`, `Web/JavaScript/Reference/Global_Objects/Array/push`, `Web/JavaScript/Guide/Indexed_collections`, `Web/JavaScript/Reference/Global_Objects/Array`, `Web/JavaScript/Reference/Global_Objects/Array/toReversed`, `Web/JavaScript/Reference/Global_Objects/Array/concat`, `Web/JavaScript/Reference/Global_Objects/Array/pop`

**s02** (similar): какой метод массива отбирает элементы по условию

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/filter`
- найдено: `Web/JavaScript/Reference/Global_Objects/Array/every`, `Web/JavaScript/Reference/Global_Objects/Array/some`, `Web/JavaScript/Guide/Indexed_collections`, `Web/JavaScript/Guide/Language_overview`, `Web/JavaScript/Reference/Global_Objects/Array/lastIndexOf`, `Web/JavaScript/Reference/Global_Objects/Array/includes`

**s03** (similar): какой метод перебирает массив и ничего не возвращает

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/forEach`
- найдено: `Web/JavaScript/Guide/Indexed_collections`, `Web/JavaScript/Reference/Global_Objects/Array/pop`, `Web/JavaScript/Reference/Global_Objects/Array`, `Web/JavaScript/Reference/Global_Objects/RegExp/exec`, `Web/JavaScript/Reference/Global_Objects/Array/find`, `Web/JavaScript/Guide/Language_overview`, `Web/JavaScript/Reference/Global_Objects/Array/toReversed`, `Web/JavaScript/Reference/Global_Objects/Array/slice`

**s05** (similar): какое объявление переменной запрещает повторное присваивание

- ожидалось: `Web/JavaScript/Reference/Statements/const`
- найдено: `Web/JavaScript/Guide/Grammar_and_types`, `Web/JavaScript/Reference/Errors/Redeclared_parameter`, `Web/JavaScript/Guide/Language_overview`, `Web/JavaScript/Reference/Global_Objects/Object/preventExtensions`, `Web/JavaScript/Reference/Statements/var`, `Web/JavaScript/Reference/Statements`

**s06** (similar): какое объявление переменной разрешает менять значение

- ожидалось: `Web/JavaScript/Reference/Statements/let`
- найдено: `Web/JavaScript/Guide/Grammar_and_types`, `Web/JavaScript/Guide/Language_overview`, `Web/JavaScript/Reference/Statements/var`, `Web/JavaScript/Reference/Statements`, `Web/JavaScript/Reference/Statements/const`

**s07** (similar): выравнивание по главной оси флекс-контейнера

- ожидалось: `Web/CSS/Reference/Properties/justify-content`
- найдено: `Web/CSS/Guides/Flexible_box_layout/Aligning_items`, `Web/CSS/Guides/Box_alignment/In_flexbox`

**s08** (similar): выравнивание по поперечной оси флекс-контейнера

- ожидалось: `Web/CSS/Reference/Properties/align-items`
- найдено: `Web/CSS/Guides/Flexible_box_layout/Aligning_items`, `Web/CSS/Guides/Box_alignment/In_flexbox`, `Web/CSS/Reference/Properties/place-items`

**c04** (cross): как закешировать статику чтобы браузер не запрашивал её каждый раз

- ожидалось: `Web/HTTP/Reference/Headers/Cache-Control`
- найдено: `Web/HTML/How_to/Author_fast-loading_HTML_pages`, `Web/HTTP/Guides/Caching`, `Web/JavaScript/Reference/Global_Objects/RegExp/n`, `Web/HTTP/Guides/Session`, `Web/HTTP/Reference/Headers/Set-Cookie`, `Web/JavaScript/Reference/Classes/static`, `Glossary/Request_header`

### `vector_nocode`

**n02** (natural): как из массива цен получить массив цен со скидкой

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/map`
- найдено: `Glossary/Array`, `Web/JavaScript/Reference/Global_Objects/Object/values`, `Web/JavaScript/Reference/Global_Objects/Array/slice`, `Web/JavaScript/Guide/Language_overview`, `Web/JavaScript/Reference/Global_Objects/Array/reduce`, `Web/JavaScript/Reference/Errors/Reduce_of_empty_array_with_no_initial_value`, `Web/JavaScript/Guide/Indexed_collections`

**n04** (natural): пишу obj.user.name и падает ошибка если user нет

- ожидалось: `Web/JavaScript/Reference/Operators/Optional_chaining`
- найдено: `Web/JavaScript/Reference/Errors/Missing_name_after_dot_operator`, `Web/JavaScript/Reference/Global_Objects/ReferenceError`, `Web/JavaScript/Reference/Global_Objects/Symbol/unscopables`, `Web/JavaScript/Reference/Errors/Unnamed_function_statement`, `Web/JavaScript/Reference/Global_Objects/SyntaxError`, `Web/JavaScript/Reference/Global_Objects/Reflect/defineProperty`, `Web/JavaScript/Reference/Operators/Property_accessors`, `Web/JavaScript/Reference/Errors/Missing_parenthesis_after_condition`

**n10** (natural): объявил переменную в цикле, а снаружи её не видно, почему

- ожидалось: `Web/JavaScript/Reference/Statements/let`
- найдено: `Web/JavaScript/Guide/Grammar_and_types`, `Web/JavaScript/Reference/Statements/var`, `Web/JavaScript/Guide/Closures`, `Web/JavaScript/Reference/Statements/block`, `Web/JavaScript/Reference/Errors/Undeclared_var`, `Web/JavaScript/Guide/Language_overview`, `Web/JavaScript/Guide/Functions`

**n11** (natural): как дождаться пока загрузятся данные и потом их показать

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Promise`
- найдено: `Web/HTML/How_to/Author_fast-loading_HTML_pages`, `Glossary/First_input_delay`, `Glossary/Hoisting`, `Web/JavaScript/Reference/Global_Objects/DataView/byteOffset`, `Web/JavaScript/Reference/Operators/async_function`, `Web/JavaScript/Reference/Global_Objects/DataView/buffer`, `Web/JavaScript/Reference/Global_Objects/DataView/setInt8`, `Web/JavaScript/Reference/Global_Objects/DataView/byteLength`, `Web/JavaScript/Guide/Control_flow_and_error_handling`

**n12** (natural): хочу прижать элемент к низу экрана чтобы он не уезжал при прокрутке

- ожидалось: `Web/CSS/Reference/Properties/position`
- найдено: `Web/CSS/Reference/Properties/background-attachment`, `Web/CSS/Reference/Properties/overscroll-behavior`, `Web/CSS/Reference/Properties/scroll-snap-type`, `Web/CSS/Reference/At-rules/@media/prefers-reduced-motion`, `Web/CSS/Reference/Properties/scroll-behavior`, `Web/CSS/Reference/Properties/cursor`, `Web/CSS/Reference/Selectors/:target`

**s01** (similar): какой метод массива возвращает новый массив той же длины

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/map`
- найдено: `Web/JavaScript/Reference/Global_Objects/Array/slice`, `Web/JavaScript/Reference/Global_Objects/Array/unshift`, `Web/JavaScript/Reference/Global_Objects/Array/push`, `Web/JavaScript/Guide/Indexed_collections`, `Web/JavaScript/Reference/Global_Objects/Array`, `Web/JavaScript/Reference/Global_Objects/Array/toReversed`, `Web/JavaScript/Reference/Global_Objects/Array/concat`, `Web/JavaScript/Reference/Global_Objects/Array/pop`

**s02** (similar): какой метод массива отбирает элементы по условию

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/filter`
- найдено: `Web/JavaScript/Reference/Global_Objects/Array/every`, `Web/JavaScript/Reference/Global_Objects/Array/some`, `Web/JavaScript/Guide/Indexed_collections`, `Web/JavaScript/Guide/Language_overview`, `Web/JavaScript/Reference/Global_Objects/Array/lastIndexOf`, `Web/JavaScript/Reference/Global_Objects/Array/includes`

**s03** (similar): какой метод перебирает массив и ничего не возвращает

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/forEach`
- найдено: `Web/JavaScript/Guide/Indexed_collections`, `Web/JavaScript/Reference/Global_Objects/Array/pop`, `Web/JavaScript/Reference/Global_Objects/Array`, `Web/JavaScript/Reference/Global_Objects/RegExp/exec`, `Web/JavaScript/Reference/Global_Objects/Array/find`, `Web/JavaScript/Guide/Language_overview`, `Web/JavaScript/Reference/Global_Objects/Array/toReversed`, `Web/JavaScript/Reference/Global_Objects/Array/slice`

**s05** (similar): какое объявление переменной запрещает повторное присваивание

- ожидалось: `Web/JavaScript/Reference/Statements/const`
- найдено: `Web/JavaScript/Guide/Grammar_and_types`, `Web/JavaScript/Reference/Errors/Redeclared_parameter`, `Web/JavaScript/Guide/Language_overview`, `Web/JavaScript/Reference/Global_Objects/Object/preventExtensions`, `Web/JavaScript/Reference/Statements/var`, `Web/JavaScript/Reference/Statements`

**s06** (similar): какое объявление переменной разрешает менять значение

- ожидалось: `Web/JavaScript/Reference/Statements/let`
- найдено: `Web/JavaScript/Guide/Grammar_and_types`, `Web/JavaScript/Guide/Language_overview`, `Web/JavaScript/Reference/Statements/var`, `Web/JavaScript/Reference/Statements`, `Web/JavaScript/Reference/Statements/const`

**s07** (similar): выравнивание по главной оси флекс-контейнера

- ожидалось: `Web/CSS/Reference/Properties/justify-content`
- найдено: `Web/CSS/Guides/Flexible_box_layout/Aligning_items`, `Web/CSS/Guides/Box_alignment/In_flexbox`

**s08** (similar): выравнивание по поперечной оси флекс-контейнера

- ожидалось: `Web/CSS/Reference/Properties/align-items`
- найдено: `Web/CSS/Guides/Flexible_box_layout/Aligning_items`, `Web/CSS/Guides/Box_alignment/In_flexbox`

**c04** (cross): как закешировать статику чтобы браузер не запрашивал её каждый раз

- ожидалось: `Web/HTTP/Reference/Headers/Cache-Control`
- найдено: `Web/HTML/How_to/Author_fast-loading_HTML_pages`, `Web/HTTP/Guides/Caching`, `Web/JavaScript/Reference/Global_Objects/RegExp/n`, `Web/HTTP/Guides/Session`, `Web/HTTP/Reference/Headers/Set-Cookie`, `Web/JavaScript/Reference/Classes/static`, `Web/CSS/Reference/Properties/overflow`
