import sys
from pathlib import Path
from datetime import datetime

from engine.config_engine import (  # 🔧 МОЖНО МЕНЯТЬ: настройки движка/редактора
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    FPS,
    PROJECTS_DIR,
)

from editor.editor_app import run_editor  # 🧠 ЛОГИКА: запуск редактора


def _setup_file_logging() -> None:
    """
    🧠 ЛОГИКА:
    Когда запускаем через pythonw.exe — консоли нет, поэтому stdout/stderr пропадают.
    Мы перенаправляем их в engine_log.txt.
    """
    log_path = Path(__file__).resolve().parent / "engine_log.txt"

    # ✅ line-buffered: будет писать построчно, а не "когда-нибудь потом"
    f = open(log_path, "a", encoding="utf-8", buffering=1)

    sys.stdout = f  # type: ignore[assignment]
    sys.stderr = f  # type: ignore[assignment]

    print("\n" + "=" * 60)
    print("DragonEngine старт:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)


def main():
    """🧠 ЛОГИКА: точка входа движка."""
    _setup_file_logging()

    run_editor(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        window_title=WINDOW_TITLE,
        fps=FPS,
        projects_dir=PROJECTS_DIR,
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print("ENGINE CRASH:", e)
        raise
