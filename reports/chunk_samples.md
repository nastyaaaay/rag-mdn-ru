# Примеры фрагментов

Так выглядит то, что попадёт в векторную базу. Каждый фрагмент показан ровно в том виде, в каком уйдёт в модель эмбеддингов — вместе с путём заголовков в первой строке.

## Фрагмент 1: Date.prototype.setMilliseconds()

- Источник: https://developer.mozilla.org/ru/docs/Web/JavaScript/Reference/Global_Objects/Date/setMilliseconds
- Длина: 461 символов

````
Date.prototype.setMilliseconds()

Если значение параметра `millisecondsValue` будет выходить за пределы ожидаемого диапазона, метод `setMilliseconds()` соответственно обновит объект Date. Например, если в качестве `millisecondsValue` передать значение 1005, количество секунд увеличится на 1, а в качестве миллисекунд будет использоваться значение 5.

```js
var theBigDay = new Date();
theBigDay.setMilliseconds(100);
```

- Date.prototype.getMilliseconds()
- Date.prototype.setUTCMilliseconds()
````

## Фрагмент 2: delete

- Источник: https://developer.mozilla.org/ru/docs/Web/JavaScript/Reference/Operators/delete
- Длина: 372 символов

````
delete › Синтаксис

- `object` — Имя объекта или выражение, результатом вычисления которого является объект.
- `property` — Удаляемое свойство.
- `index` — Целое число, представляющее собой индекс массива, который должен быть удалён.

Возвращает false, только если свойство существует в самом объекте, а не в его прототипах, и не может быть удалено. Во всех остальных случаях возвращает true.
````

## Фрагмент 3: background-size

- Источник: https://developer.mozilla.org/ru/docs/Web/CSS/Reference/Properties/background-size
- Длина: 494 символов

````
background-size › Примеры

Эта демонстрация `background-size: cover` и эта демонстрация `background-size: contain` предназначены для открытия в новых окнах, чтобы вы могли видеть, как `contain` и `cover` ведут себя, когда размеры области расположения фона изменяются. Эта серия демонстраций, как работает `background-size` и взаимодействует с другими свойствами `background-*`, должна в значительной степени охватить оставшуюся основу в том, как использовать `background-size` отдельно и в сочетании с другими свойствами.
````

## Фрагмент 4: <header>

- Источник: https://developer.mozilla.org/ru/docs/Web/HTML/Reference/Elements/header
- Длина: 441 символов

````
<header>

```css interactive-example
.logo {
  background: left / cover
    url("/shared-assets/images/examples/puppy-header.jpg");
  display: flex;
  height: 120px;
  align-items: center;
  justify-content: center;
  font:
    bold calc(1em + 2 * (100vw - 120px) / 100) "Dancing Script",
    fantasy;
  color: #ff0083;
  text-shadow: #000 2px 2px 0.2rem;
}

header > h1 {
  margin-bottom: 0;
}

header > time {
  font: italic 0.7rem sans-serif;
}
```
````
