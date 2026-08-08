"""Загрузка нужных разделов MDN без клонирования всего репозитория.

Полный репозиторий mdn/translated-content — сотни мегабайт, а нужные нам
разделы — около 8 МБ текста. Используем частичный клон Git (`--filter
blob:none`) и разреженную выкладку (`sparse-checkout`): Git скачивает
только объекты из перечисленных папок, а не всё дерево репозитория.
"""

import subprocess
from pathlib import Path

from ragmdn.config import Settings


class DownloadError(RuntimeError):
    """Git завершился с ошибкой при загрузке корпуса."""


def _run(args: list[str], *, cwd: Path | None = None) -> None:
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        command = " ".join(args)
        raise DownloadError(
            f"команда `{command}` завершилась с кодом {result.returncode}:\n{result.stderr}"
        )


def sync_corpus(settings: Settings) -> Path:
    """Скачивает (или обновляет) выбранные разделы MDN.

    Возвращает путь к папке `files/ru` внутри локальной копии репозитория —
    именно её дальше обходит сборщик отчёта.
    """
    repo_dir = settings.raw_dir / "mdn-translated-content"
    repo_url = f"https://github.com/{settings.mdn_repo}.git"
    sparse_paths = [f"files/ru/{area}" for area in settings.mdn_areas]

    if not (repo_dir / ".git").exists():
        repo_dir.mkdir(parents=True, exist_ok=True)
        _run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                "--depth",
                "1",
                "--branch",
                settings.mdn_branch,
                repo_url,
                str(repo_dir),
            ]
        )
        _run(["git", "sparse-checkout", "init", "--cone"], cwd=repo_dir)

    _run(["git", "sparse-checkout", "set", *sparse_paths], cwd=repo_dir)
    _run(["git", "checkout", settings.mdn_branch], cwd=repo_dir)

    return repo_dir / "files" / "ru"
