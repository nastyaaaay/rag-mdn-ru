"""HTTP-API и веб-страница.

    uvicorn ragmdn.api:app --reload

Модель эмбеддингов грузится один раз при старте, а не на каждый запрос:
она весит 2.2 ГБ, и загрузка занимает секунды. Подключение к базе, наоборот,
берётся на каждый запрос — так проще и надёжнее, а стоит это доли миллисекунды.
"""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ragmdn.answer import answer_question
from ragmdn.config import get_settings
from ragmdn.db import IndexMismatchError, connect, count_rows
from ragmdn.embeddings import Embedder
from ragmdn.llm import LLMError, OpenAICompatibleModel
from ragmdn.search import SEARCH_METHODS, search

_state: dict[str, object] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _state["settings"] = settings
    _state["embedder"] = Embedder(settings)
    _state["model"] = OpenAICompatibleModel(settings)
    yield
    _state.clear()


app = FastAPI(
    title="RAG по документации MDN",
    description="Поиск и ответы по русской документации MDN с указанием источников",
    lifespan=lifespan,
)


class Source(BaseModel):
    title: str
    heading_path: str
    url: str
    score: float


class AskRequest(BaseModel):
    question: str = Field(min_length=3, examples=["Что возвращает метод filter у массива?"])
    method: Literal["vector", "fulltext", "hybrid"] = "vector"
    limit: int = Field(default=5, ge=1, le=20)


class AskResponse(BaseModel):
    question: str
    answer: str
    #: Система призналась, что ответа в документах нет.
    is_refusal: bool
    sources: list[Source]
    #: Модель сослалась на фрагмент, которого ей не передавали, — признак выдумки.
    has_invalid_citation: bool


class SearchResponse(BaseModel):
    question: str
    hits: list[Source]


@app.get("/health")
def health() -> dict:
    """Готовность системы: доступна ли база и есть ли в ней индекс."""
    settings = _state["settings"]
    try:
        with connect(settings) as conn:
            documents, chunks = count_rows(conn)
        return {
            "status": "ok" if chunks else "индекс пуст",
            "documents": documents,
            "chunks": chunks,
            "embedding_model": settings.embedding_model,
            "llm_model": settings.llm_model,
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"база недоступна: {exc}") from exc


@app.post("/search", response_model=SearchResponse)
def search_endpoint(request: AskRequest) -> SearchResponse:
    """Только поиск, без обращения к языковой модели."""
    settings = _state["settings"]
    try:
        with connect(settings) as conn:
            hits = search(
                conn, _state["embedder"], request.question,
                method=request.method, limit=request.limit, settings=settings,
            )
    except IndexMismatchError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"база недоступна: {exc}") from exc

    return SearchResponse(
        question=request.question,
        hits=[
            Source(title=h.title, heading_path=h.heading_path, url=h.source_url, score=h.score)
            for h in hits
        ],
    )


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    """Поиск и ответ по найденным фрагментам."""
    settings = _state["settings"]

    try:
        with connect(settings) as conn:
            hits = search(
                conn, _state["embedder"], request.question,
                method=request.method, limit=request.limit, settings=settings,
            )
    except IndexMismatchError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"база недоступна: {exc}") from exc

    try:
        result = answer_question(_state["model"], request.question, hits, settings)
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=f"модель недоступна: {exc}") from exc

    return AskResponse(
        question=request.question,
        answer=result.text,
        is_refusal=result.is_refusal,
        has_invalid_citation=result.has_invalid_citation,
        sources=[
            Source(title=h.title, heading_path=h.heading_path, url=h.source_url, score=h.score)
            for h in result.sources
        ],
    )


PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RAG по документации MDN</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         max-width: 46rem; margin: 0 auto; padding: 2rem 1rem; line-height: 1.6; }
  h1 { font-size: 1.4rem; margin-bottom: .25rem; }
  .sub { color: #666; font-size: .9rem; margin-bottom: 1.5rem; }
  form { display: flex; gap: .5rem; margin-bottom: 1rem; }
  input[type=text] { flex: 1; padding: .6rem .8rem; font-size: 1rem;
                     border: 1px solid #bbb; border-radius: .4rem; }
  button { padding: .6rem 1.2rem; font-size: 1rem; cursor: pointer;
           border: 0; border-radius: .4rem; background: #2563eb; color: #fff; }
  button:disabled { background: #9ca3af; cursor: default; }
  .answer { padding: 1rem; border-radius: .5rem; background: #f3f4f6;
            white-space: pre-wrap; }
  .refusal { background: #fef3c7; }
  .warn { background: #fee2e2; padding: .6rem 1rem; border-radius: .5rem;
          margin-top: .75rem; }
  ul { padding-left: 1.2rem; }
  li { margin: .35rem 0; }
  .muted { color: #666; font-size: .85rem; }
  @media (prefers-color-scheme: dark) {
    .answer { background: #1f2937; }
    .refusal { background: #422006; }
    .warn { background: #450a0a; }
    input[type=text] { background: #111827; color: #eee; border-color: #374151; }
  }
</style>
</head>
<body>
<h1>Вопрос по документации MDN</h1>
<p class="sub">Отвечает только по документам из индекса. Если ответа там нет —
скажет об этом прямо, а не придумает.</p>

<form id="f">
  <input type="text" id="q" placeholder="например: как отфильтровать массив" required>
  <button type="submit" id="b">Спросить</button>
</form>

<div id="out"></div>

<script>
const form = document.getElementById('f');
const out = document.getElementById('out');
const button = document.getElementById('b');

form.onsubmit = async (event) => {
  event.preventDefault();
  const question = document.getElementById('q').value.trim();
  if (!question) return;

  button.disabled = true;
  out.innerHTML = '<p class="muted">Ищу и составляю ответ, это занимает до минуты…</p>';

  try {
    const response = await fetch('/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question}),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({detail: response.statusText}));
      out.innerHTML = '<div class="warn">Ошибка: ' + error.detail + '</div>';
      return;
    }
    const data = await response.json();

    let html = '<div class="answer' + (data.is_refusal ? ' refusal' : '') + '">'
             + escapeHtml(data.answer) + '</div>';

    if (data.has_invalid_citation) {
      html += '<div class="warn">Модель сослалась на несуществующий фрагмент — '
            + 'признак выдумывания.</div>';
    }
    if (data.sources.length) {
      html += '<p><strong>Источники:</strong></p><ul>';
      for (const source of data.sources) {
        html += '<li><a href="' + source.url + '" target="_blank" rel="noopener">'
              + escapeHtml(source.heading_path) + '</a></li>';
      }
      html += '</ul>';
    }
    out.innerHTML = html;
  } catch (error) {
    out.innerHTML = '<div class="warn">Не удалось получить ответ: ' + error + '</div>';
  } finally {
    button.disabled = false;
  }
};

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE
