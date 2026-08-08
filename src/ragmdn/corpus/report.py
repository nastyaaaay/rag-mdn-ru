"""Сборка отчёта о качестве корпуса до того, как он попадёт в индекс.

Ничего не индексирует и не парсит окончательно — только считает и показывает,
что скрывается за 1429 файлами: сколько текста реально на русском, сколько
заглушек, какие макросы встречаются. Решение о пороге фильтра принимается
по цифрам из этого отчёта, а не на глаз.
"""

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from ragmdn.config import Settings
from ragmdn.corpus.frontmatter import FrontmatterError, split_frontmatter
from ragmdn.corpus.text_stats import cyrillic_ratio, extract_macro_names, is_stub, strip_markup


@dataclass(frozen=True)
class DocumentStats:
    area: str
    relative_path: str
    slug: str | None
    title: str | None
    char_count: int
    cyrillic_ratio: float
    macros: Counter[str]
    is_stub: bool


@dataclass(frozen=True)
class DocumentError:
    area: str
    relative_path: str
    reason: str


@dataclass
class CorpusReport:
    documents: list[DocumentStats] = field(default_factory=list)
    errors: list[DocumentError] = field(default_factory=list)

    @property
    def total_found(self) -> int:
        return len(self.documents) + len(self.errors)

    def kept(self, threshold: float) -> list[DocumentStats]:
        return [d for d in self.documents if not d.is_stub and d.cyrillic_ratio >= threshold]

    def excluded_by_language(self, threshold: float) -> list[DocumentStats]:
        return [d for d in self.documents if not d.is_stub and d.cyrillic_ratio < threshold]

    def stubs(self) -> list[DocumentStats]:
        return [d for d in self.documents if d.is_stub]

    def macro_frequency(self) -> Counter[str]:
        total: Counter[str] = Counter()
        for doc in self.documents:
            total.update(doc.macros)
        return total

    def ratio_histogram(self, bucket_size: float = 0.1) -> Counter[int]:
        """Ключ — номер интервала: 0 значит [0%,10%), ..., 9 значит [90%,100%]."""
        histogram: Counter[int] = Counter()
        bucket_count = round(1 / bucket_size)
        for doc in self.documents:
            if doc.is_stub:
                continue
            bucket = min(int(doc.cyrillic_ratio / bucket_size), bucket_count - 1)
            histogram[bucket] += 1
        return histogram


def build_report(root: Path, settings: Settings) -> CorpusReport:
    """Обходит все документы выбранных разделов и считает по ним статистику."""
    report = CorpusReport()

    for area in settings.mdn_areas:
        area_dir = root / area
        if not area_dir.exists():
            report.errors.append(
                DocumentError(
                    area=area,
                    relative_path=area,
                    reason="папка не найдена после синхронизации — проверьте sparse-checkout",
                )
            )
            continue

        for md_path in sorted(area_dir.rglob("index.md")):
            relative_path = str(md_path.relative_to(root)).replace("\\", "/")
            try:
                raw = md_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                report.errors.append(
                    DocumentError(area=area, relative_path=relative_path, reason=str(exc))
                )
                continue

            try:
                fields, body = split_frontmatter(raw)
            except FrontmatterError as exc:
                report.errors.append(
                    DocumentError(area=area, relative_path=relative_path, reason=str(exc))
                )
                continue

            char_count = len(body.strip())
            stub = is_stub(body, settings.min_document_chars)
            ratio = 0.0 if stub else cyrillic_ratio(strip_markup(body))

            report.documents.append(
                DocumentStats(
                    area=area,
                    relative_path=relative_path,
                    slug=fields.get("slug"),
                    title=fields.get("title"),
                    char_count=char_count,
                    cyrillic_ratio=ratio,
                    macros=extract_macro_names(body),
                    is_stub=stub,
                )
            )

    return report


def write_csv(report: CorpusReport, path: Path) -> None:
    """Построчный список документов — для ручной проверки границы порога."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["area", "path", "slug", "char_count", "cyrillic_ratio", "is_stub"])
        for doc in sorted(report.documents, key=lambda d: d.cyrillic_ratio):
            writer.writerow(
                [doc.area, doc.relative_path, doc.slug or "", doc.char_count,
                 f"{doc.cyrillic_ratio:.4f}", int(doc.is_stub)]
            )


def _bar(count: int, max_count: int, width: int = 40) -> str:
    if max_count == 0:
        return ""
    filled = round(width * count / max_count)
    return "█" * filled


def render_markdown(report: CorpusReport, settings: Settings) -> str:
    threshold = settings.min_cyrillic_ratio
    kept = report.kept(threshold)
    excluded = report.excluded_by_language(threshold)
    stubs = report.stubs()
    histogram = report.ratio_histogram()
    max_bucket = max(histogram.values(), default=0)

    lines: list[str] = []
    lines.append("# Отчёт о качестве корпуса MDN")
    lines.append("")
    lines.append(
        f"Найдено файлов: **{report.total_found}**, "
        f"успешно разобрано: **{len(report.documents)}**, "
        f"ошибок разбора: **{len(report.errors)}**."
    )
    lines.append("")
    lines.append(
        f"При пороге доли кириллицы **{threshold:.0%}**: "
        f"включено в индекс **{len(kept)}**, "
        f"исключено как непереведённые **{len(excluded)}**, "
        f"исключено как заглушки **{len(stubs)}**."
    )
    lines.append("")

    lines.append("## Документов по разделам")
    lines.append("")
    lines.append("| Раздел | Найдено | Включено при текущем пороге |")
    lines.append("|---|---:|---:|")
    for area in settings.mdn_areas:
        area_docs = [d for d in report.documents if d.area == area]
        area_kept = [d for d in area_docs if not d.is_stub and d.cyrillic_ratio >= threshold]
        lines.append(f"| `{area}` | {len(area_docs)} | {len(area_kept)} |")
    lines.append("")

    lines.append("## Распределение доли кириллицы в прозе")
    lines.append("")
    lines.append("Код и инлайн-код исключены из подсчёта — считается только обычный текст.")
    lines.append("")
    lines.append("```")
    for bucket in range(10):
        count = histogram.get(bucket, 0)
        low, high = bucket * 10, bucket * 10 + 10
        lines.append(f"{low:>3}-{high:<3}% | {_bar(count, max_bucket)} {count}")
    lines.append("```")
    lines.append("")

    lines.append("## Документы у границы порога (для ручной проверки)")
    lines.append("")
    lines.append(
        f"Все документы, чья доля кириллицы попадает в диапазон "
        f"[{max(threshold - 0.1, 0):.0%}, {min(threshold + 0.1, 1):.0%}] — "
        "именно на этой границе фильтр может ошибиться в обе стороны."
    )
    lines.append("")
    border_low, border_high = max(threshold - 0.1, 0.0), min(threshold + 0.1, 1.0)
    border_docs = sorted(
        (d for d in report.documents if not d.is_stub and border_low <= d.cyrillic_ratio <= border_high),
        key=lambda d: d.cyrillic_ratio,
    )
    if border_docs:
        lines.append("| Доля кириллицы | Раздел | Путь |")
        lines.append("|---:|---|---|")
        for doc in border_docs[:25]:
            lines.append(f"| {doc.cyrillic_ratio:.0%} | `{doc.area}` | `{doc.relative_path}` |")
        if len(border_docs) > 25:
            lines.append(f"| ... | и ещё {len(border_docs) - 25} документов | |")
    else:
        lines.append("Документов у границы не найдено.")
    lines.append("")

    lines.append("## Заглушки")
    lines.append("")
    lines.append(f"Всего: {len(stubs)} (короче {settings.min_document_chars} символов).")
    if stubs:
        lines.append("")
        lines.append("| Раздел | Путь | Символов |")
        lines.append("|---|---|---:|")
        for doc in stubs[:20]:
            lines.append(f"| `{doc.area}` | `{doc.relative_path}` | {doc.char_count} |")
        if len(stubs) > 20:
            lines.append(f"| ... | и ещё {len(stubs) - 20} документов | |")
    lines.append("")

    lines.append("## Макросы MDN")
    lines.append("")
    macro_freq = report.macro_frequency()
    lines.append(f"Всего различных макросов: {len(macro_freq)}.")
    lines.append("")
    lines.append("| Макрос | Встречается раз |")
    lines.append("|---|---:|")
    for name, count in macro_freq.most_common(30):
        lines.append(f"| `{{{{{name}}}}}` | {count} |")
    lines.append("")

    if report.errors:
        lines.append("## Ошибки разбора")
        lines.append("")
        lines.append("| Раздел | Путь | Причина |")
        lines.append("|---|---|---|")
        for err in report.errors[:30]:
            lines.append(f"| `{err.area}` | `{err.relative_path}` | {err.reason} |")
        lines.append("")

    return "\n".join(lines)
