"""Проверка обоснованности ответов моделью-судьёй.

    python -m ragmdn.evaluation.run_judge

Работает по готовым ответам из `reports/answers.json` — генерация занимает
полчаса, и гонять её ради каждой метрики бессмысленно.

Отдельно считается **согласие судьи с независимой разметкой**. Без этого
числа «обоснованность 85%» — оценка, взятая у модели на слово, а весь смысл
проекта в том, чтобы на слово ничего не брать.
"""

import functools
import json
import sys
from collections import Counter

from ragmdn.config import get_settings
from ragmdn.evaluation.generation import load_records
from ragmdn.evaluation.judge import (
    Judgement,
    Verdict,
    agreement_rate,
    groundedness,
    judge_answer,
)
from ragmdn.llm import LLMError, OpenAICompatibleModel

print = functools.partial(print, flush=True)  # noqa: A001

GROUP_TITLES = {
    "direct": "прямые вопросы",
    "natural": "своими словами",
    "similar": "различение похожих",
    "trap": "ловушки",
    "cross": "на стыке тем",
}


def load_manual_labels(path) -> dict[str, Verdict]:
    """Читает независимую разметку, если она есть."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {qid: Verdict(value) for qid, value in data.items()}


def render_report(records, judgements, manual, agreement, disagreements, settings) -> str:
    by_id = {r.question_id: r for r in records}
    scored = [j for j in judgements if not by_id[j.question_id].is_refusal]

    lines = ["# Обоснованность ответов (оценка моделью-судьёй)", ""]
    lines.append(f"Судья: `{settings.llm_model}` — **та же модель, что и отвечает**.")
    lines.append("")
    lines.append("> Метрики этого отчёта получены от языковой модели, а не вычислены")
    lines.append("> кодом. Судья ошибается, поэтому ниже отдельно измерено его согласие")
    lines.append("> с независимой разметкой — все остальные цифры читаются с этой поправкой.")
    lines.append("")

    lines.append("## Обоснованность")
    lines.append("")
    lines.append(
        f"Средняя обоснованность содержательных ответов: "
        f"**{groundedness(scored):.0%}** (оценено {len(scored)} ответов; "
        "отказы не оцениваются — в них нечего проверять)."
    )
    lines.append("")
    counts = Counter(j.verdict for j in scored)
    lines.append("| Вердикт | Ответов |")
    lines.append("|---|---:|")
    for verdict in Verdict:
        if counts.get(verdict):
            lines.append(f"| {verdict.value} | {counts[verdict]} |")
    lines.append("")

    if counts.get(Verdict.UNPARSABLE):
        lines.append(
            f"**{counts[Verdict.UNPARSABLE]} вердиктов не удалось разобрать** — "
            "судья ответил не одним словом, как требовалось. Такие случаи "
            "засчитаны как необоснованные, то есть строго."
        )
        lines.append("")

    lines.append("## По группам вопросов")
    lines.append("")
    lines.append("| Группа | Оценено | Обоснованность |")
    lines.append("|---|---:|---:|")
    groups: dict[str, list[Judgement]] = {}
    for judgement in scored:
        groups.setdefault(by_id[judgement.question_id].group, []).append(judgement)
    for group, items in sorted(groups.items()):
        title = GROUP_TITLES.get(group, group)
        lines.append(f"| {title} | {len(items)} | {groundedness(items):.0%} |")
    lines.append("")

    lines.append("## Насколько можно верить судье")
    lines.append("")
    if manual:
        lines.append(
            f"Согласие с независимой разметкой: **{agreement:.0%}** "
            f"на {len(manual)} размеченных ответах."
        )
        lines.append("")
        if disagreements:
            lines.append("Расхождения:")
            lines.append("")
            for line in disagreements:
                lines.append(f"- {line}")
            lines.append("")
        lines.append(
            "Это поправочный коэффициент ко всем цифрам выше: обоснованность "
            f"{groundedness(scored):.0%} измерена инструментом, который сам "
            f"попадает в цель в {agreement:.0%} случаев."
        )
    else:
        lines.append(
            "Разметки нет — файл `eval/judge_labels.json` отсутствует. "
            "Пока его нет, цифры выше не подкреплены ничем, кроме доверия "
            "к языковой модели."
        )
    lines.append("")

    ungrounded = [j for j in scored if j.verdict in (Verdict.UNGROUNDED, Verdict.PARTIAL)]
    if ungrounded:
        lines.append("## Ответы, которые судья счёл необоснованными")
        lines.append("")
        for judgement in ungrounded:
            record = by_id[judgement.question_id]
            lines.append(f"**{record.question_id}** ({judgement.verdict.value}): {record.question}")
            lines.append("")
            lines.append(f"> {record.answer[:300]}")
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    settings = get_settings()
    answers_path = settings.reports_dir / "answers.json"

    if not answers_path.exists():
        print(
            "Нет файла с ответами. Сначала выполните: "
            "python -m ragmdn.evaluation.run_generation",
            file=sys.stderr,
        )
        return 1

    records = load_records(answers_path)
    print(f"Ответов на проверку: {len(records)}")
    print(f"Судья: {settings.llm_model}\n")

    model = OpenAICompatibleModel(settings)
    judgements: list[Judgement] = []

    try:
        for number, record in enumerate(records, start=1):
            judgements.append(judge_answer(model, record))
            if number % 10 == 0:
                print(f"  {number}/{len(records)}")
    except LLMError as exc:
        print(f"\nСудья недоступен: {exc}", file=sys.stderr)
        return 1

    manual = load_manual_labels(settings.project_root / "eval" / "judge_labels.json")
    agreement, disagreements = agreement_rate(judgements, manual)

    by_id = {r.question_id: r for r in records}
    scored = [j for j in judgements if not by_id[j.question_id].is_refusal]

    print("")
    print("=== Итог ===")
    print(f"Обоснованность:        {groundedness(scored):.0%} (по {len(scored)} ответам)")
    if manual:
        print(f"Согласие с разметкой:  {agreement:.0%} (на {len(manual)} примерах)")
    else:
        print("Согласие с разметкой:  не измерено — нет eval/judge_labels.json")

    report_path = settings.reports_dir / "judge_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_report(records, judgements, manual, agreement, disagreements, settings),
        encoding="utf-8",
    )
    print(f"\nОтчёт: {report_path}")

    verdicts_path = settings.reports_dir / "judgements.json"
    verdicts_path.write_text(
        json.dumps(
            {j.question_id: j.verdict.value for j in judgements}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    print(f"Вердикты: {verdicts_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
