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

## Способ поиска: `hybrid`

| Группа вопросов | Вопросов | R@1 | R@3 | R@5 | R@10 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| cross | 5 | 60% | 80% | 80% | 80% | 0.700 |
| direct | 15 | 73% | 87% | 93% | 100% | 0.825 |
| natural | 12 | 8% | 42% | 50% | 67% | 0.263 |
| similar | 10 | 10% | 30% | 30% | 30% | 0.183 |
| ВСЕГО | 42 | 38% | 60% | 64% | 71% | 0.497 |

Не найдено вовсе: 12 вопросов — `n02`, `n04`, `n10`, `n12`, `s01`, `s02`, `s03`, `s05`, `s06`, `s07`, `s08`, `c04`

## Способ поиска: `fulltext`

| Группа вопросов | Вопросов | R@1 | R@3 | R@5 | R@10 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| cross | 5 | 0% | 0% | 0% | 0% | 0.000 |
| direct | 15 | 13% | 20% | 20% | 20% | 0.156 |
| natural | 12 | 0% | 0% | 0% | 0% | 0.000 |
| similar | 10 | 0% | 0% | 0% | 0% | 0.000 |
| ВСЕГО | 42 | 5% | 7% | 7% | 7% | 0.056 |

Не найдено вовсе: 39 вопросов — `d02`, `d05`, `d06`, `d07`, `d08`, `d09`, `d10`, `d11`, `d12`, `d13`, `d14`, `d15`, `n01`, `n02`, `n03`, `n04`, `n05`, `n06`, `n07`, `n08`, `n09`, `n10`, `n11`, `n12`, `s01`, `s02`, `s03`, `s04`, `s05`, `s06`, `s07`, `s08`, `s09`, `s10`, `c01`, `c02`, `c03`, `c04`, `c05`

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

### `hybrid`

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
- найдено: `Web/JavaScript/Guide/Indexed_collections`, `Web/JavaScript/Guide/Working_with_objects`, `Web/JavaScript/Reference/Global_Objects/Array/pop`, `Web/JavaScript/Reference/Global_Objects/Array`, `Web/JavaScript/Reference/Global_Objects/RegExp/exec`, `Web/JavaScript/Reference/Global_Objects/Array/find`, `Web/JavaScript/Guide/Language_overview`, `Web/JavaScript/Reference/Global_Objects/Array/toReversed`

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

### `fulltext`

**d02** (direct): Какие аргументы получает функция обратного вызова в методе map?

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/map`
- найдено: —

**d05** (direct): В каких состояниях может находиться промис?

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Promise`
- найдено: —

**d06** (direct): Что делает оператор опциональной цепочки?

- ожидалось: `Web/JavaScript/Reference/Operators/Optional_chaining`
- найдено: —

**d07** (direct): Что означает код состояния HTTP 404?

- ожидалось: `Web/HTTP/Reference/Status/404`
- найдено: —

**d08** (direct): Чем отличается постоянное перенаправление 301 от временного?

- ожидалось: `Web/HTTP/Reference/Status/301`
- найдено: `Web/HTTP/Reference/Status/307`

**d09** (direct): Для чего нужен заголовок Cache-Control?

- ожидалось: `Web/HTTP/Reference/Headers/Cache-Control`
- найдено: —

**d10** (direct): Что такое CORS и зачем он нужен?

- ожидалось: `Glossary/CORS`, `Web/HTTP/Guides/CORS`
- найдено: —

**d11** (direct): Как свойство justify-content выравнивает элементы?

- ожидалось: `Web/CSS/Reference/Properties/justify-content`
- найдено: `Web/CSS/Guides/Flexible_box_layout/Aligning_items`, `Web/CSS/Reference/Properties/align-items`

**d12** (direct): Какие значения принимает свойство position?

- ожидалось: `Web/CSS/Reference/Properties/position`
- найдено: —

**d13** (direct): Что делает метод reduce у массива?

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/reduce`
- найдено: —

**d14** (direct): Что произойдёт при разборе некорректного JSON методом parse?

- ожидалось: `Web/JavaScript/Reference/Global_Objects/JSON/parse`
- найдено: —

**d15** (direct): Чем отличается display block от inline?

- ожидалось: `Web/CSS/Reference/Properties/display`
- найдено: `Web/CSS/Guides/Display/Block_formatting_context`, `Web/CSS/Reference/Values/revert`

**n01** (natural): у меня есть список товаров, хочу оставить только дешевле тысячи

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/filter`
- найдено: —

**n02** (natural): как из массива цен получить массив цен со скидкой

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/map`
- найдено: —

**n03** (natural): как посчитать сумму всех чисел в массиве

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/reduce`
- найдено: —

**n04** (natural): пишу obj.user.name и падает ошибка если user нет

- ожидалось: `Web/JavaScript/Reference/Operators/Optional_chaining`
- найдено: —

**n05** (natural): почему браузер ругается что запрос к чужому сайту заблокирован

- ожидалось: `Glossary/CORS`, `Web/HTTP/Guides/CORS`
- найдено: —

**n06** (natural): не могу отцентрировать блок по горизонтали внутри контейнера

- ожидалось: `Web/CSS/Reference/Properties/justify-content`, `Web/CSS/Reference/Properties/align-items`
- найдено: —

**n07** (natural): страница не найдена, какой код должен вернуть сервер

- ожидалось: `Web/HTTP/Reference/Status/404`
- найдено: —

**n08** (natural): переехал на новый адрес, как сказать поисковикам что навсегда

- ожидалось: `Web/HTTP/Reference/Status/301`
- найдено: —

**n09** (natural): браузер показывает старую версию файла после обновления

- ожидалось: `Web/HTTP/Reference/Headers/Cache-Control`
- найдено: —

**n10** (natural): объявил переменную в цикле, а снаружи её не видно, почему

- ожидалось: `Web/JavaScript/Reference/Statements/let`
- найдено: —

**n11** (natural): как дождаться пока загрузятся данные и потом их показать

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Promise`
- найдено: —

**n12** (natural): хочу прижать элемент к низу экрана чтобы он не уезжал при прокрутке

- ожидалось: `Web/CSS/Reference/Properties/position`
- найдено: —

**s01** (similar): какой метод массива возвращает новый массив той же длины

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/map`
- найдено: —

**s02** (similar): какой метод массива отбирает элементы по условию

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/filter`
- найдено: —

**s03** (similar): какой метод перебирает массив и ничего не возвращает

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/forEach`
- найдено: `Web/JavaScript/Guide/Working_with_objects`

**s04** (similar): какой метод сворачивает массив в одно значение

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/reduce`
- найдено: —

**s05** (similar): какое объявление переменной запрещает повторное присваивание

- ожидалось: `Web/JavaScript/Reference/Statements/const`
- найдено: —

**s06** (similar): какое объявление переменной разрешает менять значение

- ожидалось: `Web/JavaScript/Reference/Statements/let`
- найдено: —

**s07** (similar): выравнивание по главной оси флекс-контейнера

- ожидалось: `Web/CSS/Reference/Properties/justify-content`
- найдено: —

**s08** (similar): выравнивание по поперечной оси флекс-контейнера

- ожидалось: `Web/CSS/Reference/Properties/align-items`
- найдено: —

**s09** (similar): код ответа при постоянном переезде страницы

- ожидалось: `Web/HTTP/Reference/Status/301`
- найдено: —

**s10** (similar): код ответа когда ресурса не существует

- ожидалось: `Web/HTTP/Reference/Status/404`
- найдено: `Web/HTTP/Reference/Status`

**c01** (cross): как отправить запрос на другой домен и обработать ответ асинхронно

- ожидалось: `Glossary/CORS`, `Web/HTTP/Guides/CORS`, `Glossary/AJAX`, `Web/JavaScript/Reference/Global_Objects/Promise`
- найдено: —

**c02** (cross): сервер вернул 404, как показать это пользователю не перезагружая страницу

- ожидалось: `Web/HTTP/Reference/Status/404`, `Glossary/AJAX`
- найдено: —

**c03** (cross): получил список от сервера, надо отфильтровать и показать

- ожидалось: `Web/JavaScript/Reference/Global_Objects/Array/filter`, `Glossary/AJAX`, `Web/JavaScript/Reference/Global_Objects/Promise`
- найдено: —

**c04** (cross): как закешировать статику чтобы браузер не запрашивал её каждый раз

- ожидалось: `Web/HTTP/Reference/Headers/Cache-Control`
- найдено: —

**c05** (cross): разобрать json от сервера и вывести только нужные поля

- ожидалось: `Web/JavaScript/Reference/Global_Objects/JSON/parse`, `Web/JavaScript/Reference/Global_Objects/Array/map`
- найдено: —
