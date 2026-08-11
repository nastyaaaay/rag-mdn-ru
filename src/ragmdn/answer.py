"""Сборка ответа из найденных фрагментов.

Здесь живёт то, ради чего затевался проект: правила, по которым модель
обязана отвечать **только** по переданным документам и признаваться, когда
ответа в них нет. Без этого RAG превращается в обычную болталку, которая
уверенно сочиняет — а измерять там нечего.

Промпт и разбор ответа отделены от самого обращения к модели (`llm.py`),
чтобы их можно было проверить тестами, не поднимая никакой модели.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from ragmdn.config import Settings
from ragmdn.llm import ChatModel, Message
from ragmdn.search import SearchHit

#: Фраза, которой модель обязана отвечать, когда ответа в документах нет.
#: Проверяется буквально, поэтому она короткая и неизменная.
NO_ANSWER = "В предоставленных документах ответа нет."

SYSTEM_PROMPT = f"""\
Ты отвечаешь на вопросы по документации MDN на русском языке.

Правила, которые нельзя нарушать:

1. Отвечай ТОЛЬКО на основании приведённых ниже фрагментов документации.
   Не добавляй ничего из собственных знаний, даже если уверен в этом.
2. Если в предоставленных фрагментах ответа нет — ответь ровно одной фразой:
   {NO_ANSWER}
   Не пытайся угадать, не предлагай похожее, не рассуждай вслух.
3. После каждого утверждения указывай номер фрагмента в квадратных скобках,
   например: Метод создаёт новый массив [1].
4. Отвечай кратко и по существу, на русском языке.
5. Если фрагменты противоречат друг другу — скажи об этом прямо.
"""

USER_TEMPLATE = """\
Фрагменты документации:

{context}

Вопрос: {question}
"""

#: Ссылка на фрагмент в ответе модели: [1], [2, 3], [1][2].
_CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


@dataclass(frozen=True)
class Answer:
    """Ответ системы вместе со всем, что нужно для его проверки."""

    question: str
    text: str
    hits: tuple[SearchHit, ...]
    #: Номера фрагментов, на которые сослалась модель (начиная с 1).
    cited: tuple[int, ...]

    @property
    def is_refusal(self) -> bool:
        """Модель призналась, что ответа в документах нет."""
        return NO_ANSWER.rstrip(".").lower() in self.text.lower()

    @property
    def sources(self) -> tuple[SearchHit, ...]:
        """Фрагменты, на которые модель действительно сослалась."""
        return tuple(
            self.hits[number - 1]
            for number in self.cited
            if 1 <= number <= len(self.hits)
        )

    @property
    def source_urls(self) -> tuple[str, ...]:
        """Адреса источников без повторов, в порядке первого упоминания."""
        return tuple(dict.fromkeys(hit.source_url for hit in self.sources))

    @property
    def has_invalid_citation(self) -> bool:
        """Модель сослалась на фрагмент, которого ей не передавали.

        Признак выдумывания, который виден без всякой модели-судьи:
        номер вне диапазона означает, что ссылка взята с потолка.
        """
        return any(number < 1 or number > len(self.hits) for number in self.cited)


def format_context(hits: Sequence[SearchHit]) -> str:
    """Нумерует фрагменты, чтобы модель могла на них ссылаться.

    Заголовок документа включается в каждый фрагмент: без него модель
    не отличит описание `filter` от описания `map` — тексты у них почти
    одинаковые, а различает их именно заголовок.
    """
    blocks = []
    for number, hit in enumerate(hits, start=1):
        blocks.append(f"[{number}] {hit.heading_path}\n{hit.content}")
    return "\n\n".join(blocks)


def extract_citations(text: str) -> tuple[int, ...]:
    """Достаёт номера фрагментов из ответа, без повторов и по порядку."""
    numbers: list[int] = []
    for match in _CITATION.finditer(text):
        for part in match.group(1).split(","):
            number = int(part.strip())
            if number not in numbers:
                numbers.append(number)
    return tuple(numbers)


def build_messages(question: str, hits: Sequence[SearchHit]) -> list[Message]:
    return [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(
            role="user",
            content=USER_TEMPLATE.format(context=format_context(hits), question=question),
        ),
    ]


def answer_question(
    model: ChatModel,
    question: str,
    hits: Sequence[SearchHit],
    settings: Settings | None = None,
) -> Answer:
    """Строит ответ по найденным фрагментам.

    Если фрагментов нет вовсе, модель не вызывается: спрашивать её не о чем,
    и любой ответ был бы выдумкой по определению.
    """
    if not hits:
        return Answer(question=question, text=NO_ANSWER, hits=(), cited=())

    limit = settings.answer_context_chunks if settings else len(hits)
    context_hits = tuple(hits[:limit])

    text = model.complete(build_messages(question, context_hits)).strip()

    return Answer(
        question=question,
        text=text,
        hits=context_hits,
        cited=extract_citations(text),
    )
