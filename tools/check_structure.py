# tools/check_structure.py

# 🧠 ЛОГИКА: базовая автоматическая проверка структуры DragonEngine

# Этот файл используется CI и НЕ должен зависеть от pygame или UI

from pathlib import Path
import sys

ROOT = Path(**file**).resolve().parents[1]

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

FORBIDDEN_DIRS = [
"**pycache**",
]

def error(msg: str):
print(f"[STRUCTURE ERROR] {msg}")
sys.exit(1)

def main():
# --- обязательные файлы и папки ---
for path in REQUIRED_PATHS:
if not path.exists():
error(f"Отсутствует обязательный путь: {path}")

```
# --- запрещённые директории ---
for forbidden in FORBIDDEN_DIRS:
    for p in ROOT.rglob(forbidden):
        error(f"Запрещённая директория в репозитории: {p}")

print("[OK] Структура проекта корректна")
```

if **name** == "**main**":
main()
