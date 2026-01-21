import json
from pathlib import Path

# ============================================================
# 🧠 ЛОГИКА: глобальные настройки движка (persisted)
# ============================================================
# 🔧 МОЖНО МЕНЯТЬ: имя файла настроек (если хочешь хранить рядом с engine_main.py)
SETTINGS_FILE = Path(__file__).resolve().parent / "engine_settings.json"

# 🔧 МОЖНО МЕНЯТЬ: дефолтные значения (если добавишь новые настройки — добавляй сюда)
DEFAULT_SETTINGS: dict = {
    "fullscreen": False,
}


def load_settings() -> dict:
    """🧠 ЛОГИКА: читаем настройки из JSON (если файла нет — отдаём дефолты)."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {**DEFAULT_SETTINGS, **data}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> None:
    """🧠 ЛОГИКА: сохраняем настройки в JSON."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        # ⚠️ Молча не падаем — настройки не должны валить движок
        pass
