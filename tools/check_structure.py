# tools/check_structure.py
# 🧠 ЛОГИКА: базовая автоматическая проверка структуры DragonEngine
# ВАЖНО: запрещённые вещи проверяем ТОЛЬКО среди файлов, отслеживаемых Git,
# чтобы CI не падал из-за временных артефактов (например, __pycache__ после compileall).

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    ROOT / "engine_main.py",
    ROOT / "PROJECT_MANIFEST.md",
    ROOT / "engine",
    ROOT / "engine" / "config_engine.py",
    ROOT / "engine" / "project_manager.py",
    ROOT / "editor",
    ROOT / "editor" / "editor_app.py",
    ROOT / "editor" / "scene_editor.py",
]

# 🔧 МОЖНО МЕНЯТЬ: запрещённые паттерны в репозитории (Git-tracked)
FORBIDDEN_GIT_PATTERNS = [
    "__pycache__/",
    ".pyc",
    ".pyo",
]


def error(msg: str):
    print(f"[STRUCTURE ERROR] {msg}")
    sys.exit(1)


def _git_ls_files(root: Path) -> list[str]:
    """🧠 ЛОГИКА: возвращаем список файлов, которые реально отслеживает Git."""
    try:
        out = subprocess.check_output(
            ["git", "ls-files"],
            cwd=str(root),
            text=True,
        )
        return [line.strip() for line in out.splitlines() if line.strip()]
    except Exception as e:
        error(f"Не удалось выполнить 'git ls-files'. Git установлен? Ошибка: {e}")
        return []


def main():
    # --- обязательные файлы и папки ---
    for path in REQUIRED_PATHS:
        if not path.exists():
            error(f"Отсутствует обязательный путь: {path}")

    # --- запрещённое в репозитории (ТОЛЬКО Git-tracked) ---
    tracked = _git_ls_files(ROOT)

    for rel in tracked:
        rel_norm = rel.replace("\\", "/")  # 🧠 ЛОГИКА: нормализуем пути
        for pat in FORBIDDEN_GIT_PATTERNS:
            if pat in rel_norm:
                error(f"Запрещённый файл/путь в репозитории (tracked): {rel_norm}")

    print("[OK] Структура проекта корректна")


if __name__ == "__main__":
    main()
