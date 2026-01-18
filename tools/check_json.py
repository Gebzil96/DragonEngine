# tools/check_json.py
# 🧠 ЛОГИКА: проверяет, что все JSON-файлы в репозитории валидны
# Не проверяет "схему", только синтаксис JSON (без зависимостей)

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

# 🔧 МОЖНО МЕНЯТЬ: какие файлы проверяем
INCLUDE_GLOBS = [
    "**/*.json",
]

# 🔧 МОЖНО МЕНЯТЬ: что исключаем (на будущее, если появятся сторонние данные)
EXCLUDE_PARTS = [
    "/.git/",
    "/__pycache__/",
]


def should_skip(path: Path) -> bool:
    s = str(path).replace("\\", "/")
    return any(part in s for part in EXCLUDE_PARTS)


def main():
    checked = 0

    for glob in INCLUDE_GLOBS:
        for p in ROOT.glob(glob):
            if not p.is_file():
                continue
            if should_skip(p):
                continue

            try:
                with open(p, "r", encoding="utf-8") as f:
                    json.load(f)
                checked += 1
            except Exception as e:
                print(f"[JSON ERROR] {p}: {e}")
                sys.exit(1)

    print(f"[OK] JSON валиден (проверено файлов: {checked})")


if __name__ == "__main__":
    main()
