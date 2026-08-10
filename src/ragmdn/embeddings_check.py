"""Проверка эмбеддингов на настоящей модели и настоящих данных.

Запуск: python -m ragmdn.embeddings_check

В отличие от test_embeddings.py (быстрые тесты с поддельным бэкендом) здесь
грузится реальная модель `intfloat/multilingual-e5-large` — при первом
запуске это скачивание около 2.24 ГБ, может занять несколько минут.

Три проверки, от самой базовой к самой содержательной:

1. Совпадает ли размерность вектора с настройками.
2. Правда ли префиксы `query:`/`passage:` меняют вектор — если бы модель
   игнорировала префикс, вся защита от путаницы в embeddings.py была бы
   бессмысленной.
3. Различает ли модель `Math.acos` и `Math.asin` — две страницы MDN,
   которые различаются в тексте одним словом («арккосинус» / «арксинус»).
   Это тот самый сценарий из PLAN.md: похожие страницы справочника — самое
   слабое место обычного поиска.
"""

import math
import sys

from ragmdn.config import get_settings
from ragmdn.corpus.parser import parse_document
from ragmdn.embeddings import Embedder


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b)


def _load_description(root, relative_path: str) -> str:
    raw = (root / relative_path).read_text(encoding="utf-8")
    doc = parse_document(raw)
    # Первый раздел документа — краткое описание метода.
    return doc.sections[0].text


def main() -> int:
    settings = get_settings()
    root = settings.raw_dir / "mdn-translated-content" / "files" / "ru"

    if not root.exists():
        print(
            "Корпус не найден. Сначала выполните: python -m ragmdn.corpus.cli",
            file=sys.stderr,
        )
        return 1

    print(f"Загружаю модель {settings.embedding_model}...")
    print("При первом запуске это скачивание ~2.24 ГБ, может занять несколько минут.")
    embedder = Embedder(settings)

    ok = True

    # --- 1. Размерность -----------------------------------------------
    vector = embedder.embed_query("тест")
    print(f"\nРазмерность вектора: {len(vector)} (в настройках: {settings.embedding_dim})")
    if len(vector) != settings.embedding_dim:
        print("ОШИБКА: размерность не совпадает с настройками", file=sys.stderr)
        ok = False

    # --- 2. Префикс меняет вектор ---------------------------------------
    as_query = embedder.embed_query("filter")
    as_passage = embedder.embed_passages(["filter"])[0]
    prefix_similarity = cosine_similarity(as_query, as_passage)
    print(f"\nОдно слово как query и как passage — похожесть: {prefix_similarity:.4f}")
    if prefix_similarity > 0.999:
        print(
            "ОШИБКА: векторы почти идентичны — похоже, префикс не влияет на результат",
            file=sys.stderr,
        )
        ok = False
    else:
        print("Префикс меняет вектор — защита от путаницы в embeddings.py работает не зря.")

    # --- 3. Math.acos против Math.asin -----------------------------------
    acos_text = _load_description(root, "web/javascript/reference/global_objects/math/acos/index.md")
    asin_text = _load_description(root, "web/javascript/reference/global_objects/math/asin/index.md")

    acos_vector, asin_vector = embedder.embed_passages([acos_text, asin_text])

    print("\n--- Math.acos() против Math.asin(): различает ли модель похожие страницы? ---")
    for query_text, expected in [("арккосинус числа", "acos"), ("арксинус числа", "asin")]:
        query_vector = embedder.embed_query(query_text)
        sim_acos = cosine_similarity(query_vector, acos_vector)
        sim_asin = cosine_similarity(query_vector, asin_vector)
        winner = "acos" if sim_acos > sim_asin else "asin"
        mark = "OK" if winner == expected else "ОШИБКА"
        print(
            f'  "{query_text}": acos={sim_acos:.4f}  asin={sim_asin:.4f}  '
            f"-> ближе {winner}, ожидали {expected}  [{mark}]"
        )
        if winner != expected:
            ok = False

    print("")
    if ok:
        print("Все проверки пройдены.")
    else:
        print("ЕСТЬ ПРОБЛЕМЫ — см. ОШИБКА выше.", file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
