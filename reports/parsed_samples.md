# Примеры разобранных документов

Так текст выглядит после парсера — именно это попадёт в индекс.

## Array.prototype.filter()

Источник: https://developer.mozilla.org/ru/docs/Web/JavaScript/Reference/Global_Objects/Array/filter

### `Array.prototype.filter()`

```
Метод **`filter()`** **создаёт новый массив со всеми элементами**, прошедшими проверку, задаваемую в передаваемой функции.

```js interactive-example
const words = ["spray", "elite", "exuberant", "destruction", "present"];

const result = words.filter((word) => word.length > 6);

console.log(result);
// Expected output: Array ["exuberant", "destruction", "present"]
```
```

### `Array.prototype.filter() › Синтаксис`

```
```js
// Стрелочная функция
filter((element) => { ... } )
filter((element, index) => { ... } )
filter((element, index, array) => { ... } )

// Колбэк-функция
filter(callbackFn)
filter(callbackFn, thisArg)

// Встроенная колбэк-функция
filter(function callbackFn(element) { ... })
filter(function callbackFn(element, index) { ... })
filter(function callbackFn(element, index, array){ ... })
filter(function callbackFn(element, index, array) { ... }, thisArg)
```
```

### `Array.prototype.filter() › Синтаксис › Параметры`

```
- `callbackFn` — Функция-предикат, которая будет вызвана для проверки каждого элемента массива. Если функция возвращает `true`, то элемент остаётся в массиве, если `false`, то удаляется.

    Принимает три аргумента
    - `element` — Текущий обрабатываемый элемент в массиве.
    - `index` (необязательный) — Индекс текущего обрабатываемого элемента в массиве.
    - `array` (необязательный) — Обрабатываемый массив, на котором был вызван метод `filter()`.

- `thisArg` (необязательный) — Значение, используемое в качестве `this` при вызове колбэк-функции `callbackFn`.
```

### `Array.prototype.filter() › Синтаксис › Возвращаемое значение`

```
Вернётся новый массив с элементами, которые прошли проверку. Если ни один элемент не прошёл проверку, то будет возвращён пустой массив.
```

### `Array.prototype.filter() › Описание`

```
Метод `filter()` вызывает переданную функцию `callback` один раз для каждого элемента, присутствующего в массиве, и создаёт новый массив со всеми значениями, для которых функция `callback` вернула значение, которое может быть приведено к `true`. Функция `callback` вызывается только для индексов массива с уже определёнными значениями; она не вызывается для индексов, которые были удалены или которым значения никогда не присваивались. Элементы массива, не прошедшие проверку функцией `callback`, просто пропускаются и не включаются в новый массив.

Функция `callback` вызывается с тремя аргументами:

1. значение элемента;
2. индекс элемента;
3. массив, по которому осуществляется проход.

Если в метод `filter()` был передан параметр `thisArg`, при вызове `callback` он будет использоваться в качестве значения `this`. В противном случае в качестве значения `this` будет использоваться значение `undefined`. В конечном итоге, значение `this`, наблюдаемое из функции `callback`, определяется согласно обычным правилам определения `this`.

Метод `filter()` не изменяет массив, для которого он был вызван.

Элементы массива, обрабатываемые методом `filter()`, устанавливается до первого вызова функции `callback`. Элементы, добавленные в массив после начала выполнения метода `filter()`, либо изменённые в процессе выполнения, не будут обработаны функцией `callback`. Соответствующим образом, если существующие элементы удаляются из массива, они также не будут обработаны

**Предупреждение:** одновременное изменение элементов, описанное в предыдущем параграфе, часто приводит к труднопонимаемому коду, поэтому не рекомендуется делать это (за исключением особых случаев).
```

### `Array.prototype.filter() › Примеры › Фильтрация всех маленьких значений`

```
Следующий пример использует `filter()` для создания отфильтрованного массива, все элементы которого больше или равны 10, а все меньшие 10 удалены.

```js
function isBigEnough(value) {
  return value >= 10;
}

let filtered = [12, 5, 8, 130, 44].filter(isBigEnough);
// массив filtered теперь содержит [12, 130, 44]
```
```

### `Array.prototype.filter() › Примеры › Найти все простые числа в массиве`

```
Следующий пример возвращает все простые числа в массиве:

```js
const array = [-3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13];

function isPrime(num) {
  for (let i = 2; num > i; i++) {
    if (num % i == 0) {
      return false;
    }
  }
  return num > 1;
}

console.log(array.filter(isPrime)); // [2, 3, 5, 7, 11, 13]
```
```

### `Array.prototype.filter() › Примеры › Фильтрация неверных записей в JSON`

```
В следующем примере метод `filter()` используется для создания отфильтрованного JSON-объекта, все элементы которого содержат ненулевое числовое поле `id`.

```js
let arr = [
  { id: 15 },
  { id: -1 },
  { id: 0 },
  { id: 3 },
  { id: 12.2 },
  {},
  { id: null },
  { id: NaN },
  { id: "undefined" },
];

let invalidEntries = 0;

function filterByID(item) {
  if (Number.isFinite(item.id) && item.id !== 0) {
    return true;
  }
  invalidEntries++;
  return false;
}

let arrByID = arr.filter(filterByID);

console.log("Отфильтрованный массив\n", arrByID);
// Отфильтрованный массив
// [{ id: 15 }, { id: -1 }, { id: 3 }, { id: 12.2 }]

console.log("Количество некорректных элементов = ", invalidEntries);
// Количество некорректных элементов = 5
```
```

### `Array.prototype.filter() › Примеры › Поиск в массиве`

```
В следующем примере `filter()` используется для фильтрации содержимого массива на основе входных данных.

```js
var fruits = ["apple", "banana", "grapes", "mango", "orange"];

/**
 * Элементы массива фильтруется на основе критериев поиска (query)
 */
function filterItems(query) {
  return fruits.filter(function (el) {
    return el.toLowerCase().indexOf(query.toLowerCase()) > -1;
  });
}

console.log(filterItems("ap")); // ['apple', 'grapes']
console.log(filterItems("an")); // ['banana', 'mango', 'orange']
```
```

### `Array.prototype.filter() › Примеры › Поиск в массиве › Реализация с использованием ES2015`

```
```js
const fruits = ["apple", "banana", "grapes", "mango", "orange"];

/**
 * Элементы массива фильтруется на основе критериев поиска (query)
 */
const filterItems = (arr, query) => {
  return arr.filter(
    (el) => el.toLowerCase().indexOf(query.toLowerCase()) !== -1,
  );
};

console.log(filterItems(fruits, "ap")); // ['apple', 'grapes']
console.log(filterItems(fruits, "an")); // ['banana', 'mango', 'orange']
```
```

### `Array.prototype.filter() › Примеры › Модификация изначального массива (изменение, добавление и удаление)`

```
В следующих примерах проверяется поведение метода `filter` при изменении массива.

```js
// Изменение всех элементов
let words = ["spray", "limit", "exuberant", "destruction", "elite", "present"];

const modifiedWords = words.filter((word, index, arr) => {
  arr[index + 1] += " extra";
  return word.length < 6;
});

console.log(modifiedWords);
// Обратите внимание, что есть три слова длиной менее 6, но так как они были изменены,
// возвращается одно слово ['spray']

// Добавление новых элементов
words = ["spray", "limit", "exuberant", "destruction", "elite", "present"];
const appendedWords = words.filter((word, index, arr) => {
  arr.push("new");
  return word.length < 6;
});

console.log(appendedWords);
// Только три слова удовлетворяют условию, хотя `words` теперь имеет куда больше слов,
// длинной меньше 6 символов: ['spray', 'limit', 'elite']

// Удаление элементов
words = ["spray", "limit", "exuberant", "destruction", "elite", "present"];
const deleteWords = words.filter((word, index, arr) => {
  arr.pop();
  return word.length < 6;
});

console.log(deleteWords);
// Заметьте, что 'elite' не получено, так как удалено из `words` до того,
// как filter смог получить его: ['spray', 'limit']
```
```

### `Array.prototype.filter() › Смотрите также`

```
- Полифил `Array.prototype.filter` в библиотеке `core-js`
- Array.prototype.forEach()
- Array.prototype.every()
- Array.prototype.some()
- Array.prototype.reduce()
- Array.prototype.find()
```

## flex-wrap

Источник: https://developer.mozilla.org/ru/docs/Web/CSS/Reference/Properties/flex-wrap

### `flex-wrap`

```
Свойство CSS **`flex-wrap`** задаёт правила вывода flex-элементов — в одну строку или в несколько, с переносом блоков. Если перенос разрешён, то возможно задать направление, в котором выводятся блоки.

```css interactive-example-choice
flex-wrap: nowrap;
```

```css interactive-example-choice
flex-wrap: wrap;
```

```css interactive-example-choice
flex-wrap: wrap-reverse;
```

```html interactive-example
<section class="default-example" id="default-example">
  <div class="transition-all" id="example-element">
    <div>Item One</div>
    <div>Item Two</div>
    <div>Item Three</div>
    <div>Item Four</div>
    <div>Item Five</div>
    <div>Item Six</div>
  </div>
</section>
```

```css interactive-example
#example-element {
  border: 1px solid #c5c5c5;
  width: 80%;
  display: flex;
}

#example-element > div {
  background-color: rgba(0, 0, 255, 0.2);
  border: 3px solid blue;
  width: 60px;
  margin: 10px;
}
```

Подробнее о свойствах и дополнительную информацию смотрите Основные понятия Flexbox.
```

### `flex-wrap › Синтаксис`

```
```css
flex-wrap: nowrap; /* Default value */
flex-wrap: wrap;
flex-wrap: wrap-reverse;

/* Глобальные значения */
flex-wrap: inherit;
flex-wrap: initial;
flex-wrap: revert;
flex-wrap: revert-layer;
flex-wrap: unset;
```

Свойство `flex-wrap` может содержать одно из следующих ниже значений.
```

### `flex-wrap › Синтаксис › Значения`

```
Допускаются следующие значения:

- `nowrap` — Расположение в одну линию, может привести к переполнению контейнера. Свойство **cross-start** эквивалентно **start** или **before** в зависимости от значения flex-direction.
- `wrap` — Расположение в несколько линий. Свойство **cross-start** эквивалентно **start** или **before** в зависимости от значения `flex-direction` и свойство **cross-end** противоположно **cross-start**.
- `wrap-reverse` — Ведёт себя так же, как и `wrap`, но **cross-start** и **cross-end** инвертированы.
```

### `flex-wrap › Примеры › HTML`

```
```html
<h4>This is an example for flex-wrap:wrap</h4>
<div class="content">
  <div class="red">1</div>
  <div class="green">2</div>
  <div class="blue">3</div>
</div>
<h4>This is an example for flex-wrap:nowrap</h4>
<div class="content1">
  <div class="red">1</div>
  <div class="green">2</div>
  <div class="blue">3</div>
</div>
<h4>This is an example for flex-wrap:wrap-reverse</h4>
<div class="content2">
  <div class="red">1</div>
  <div class="green">2</div>
  <div class="blue">3</div>
</div>
```
```

### `flex-wrap › Примеры › CSS`

```
```css
/* Common Styles */
.content,
.content1,
.content2 {
  color: #fff;
  font: 100 24px/100px sans-serif;
  height: 150px;
  text-align: center;
}

.content div,
.content1 div,
.content2 div {
  height: 50%;
  width: 50%;
}
.red {
  background: orangered;
}
.green {
  background: yellowgreen;
}
.blue {
  background: steelblue;
}

/* Flexbox Styles */
.content {
  display: flex;
  flex-wrap: wrap;
}
.content1 {
  display: flex;
  flex-wrap: nowrap;
}
.content2 {
  display: flex;
  flex-wrap: wrap-reverse;
}
```
```

### `flex-wrap › Смотрите также`

```
- Using CSS flexible boxes
```

## AJAX

Источник: https://developer.mozilla.org/ru/docs/Glossary/AJAX

### `AJAX`

```
Асинхронный JavaScript и XML (англ. **Ajax** или **AJAX**) — это подход к разработке, при котором веб-приложение запрашивает данные с сервера с помощью асинхронных HTTP-запросов и использует полученные ответы для обновления только необходимых частей документа, без полной перезагрузки страницы. Это может сделать страницу более отзывчивой, потому что запрашиваются только необходимые для обновления части.

Ajax можно использовать для создания одностраничных приложений, которые состоят из одного документа, использующего Ajax для обновления содержимого.

Изначально для реализации Ajax использовался интерфейс XMLHttpRequest, но для создания современных веб-приложений больше подходит fetch() API: он более мощный, гибкий и лучше интегрируется с фундаментальными веб-технологиями, такими как Service Worker API. Современные веб-фреймворки также предоставляют абстракции для использования Ajax.

Эта техника настолько широко распространена в современной веб-разработке, что сам термин «Ajax» сейчас используется редко.
```

### `AJAX › Смотрите также`

```
- Получение данных с сервера
- Fetch API
- Related glossary terms:
  - Одностраничное приложение
- XMLHttpRequest
- AJAX в Википедии
```
