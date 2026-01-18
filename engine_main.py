import sys  # 🧠 ЛОГИКА: корректный выход

from engine.config_engine import (  # 🔧 МОЖНО МЕНЯТЬ: настройки движка/редактора
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    FPS,
    PROJECTS_DIR,
)

from editor.editor_app import run_editor  # 🧠 ЛОГИКА: запуск редактора


def main():
    """🧠 ЛОГИКА: точка входа движка. По умолчанию стартует редактор."""
    run_editor(
        window_width=WINDOW_WIDTH,      # 🔧 МОЖНО МЕНЯТЬ: engine/config_engine.py
        window_height=WINDOW_HEIGHT,    # 🔧 МОЖНО МЕНЯТЬ: engine/config_engine.py
        window_title=WINDOW_TITLE,      # 🔧 МОЖНО МЕНЯТЬ: engine/config_engine.py
        fps=FPS,                        # 🔧 МОЖНО МЕНЯТЬ: engine/config_engine.py
        projects_dir=PROJECTS_DIR,      # 🔧 МОЖНО МЕНЯТЬ: engine/config_engine.py
    )


if __name__ == "__main__":  # 🧠 ЛОГИКА: стандартный вход
    try:
        main()              # 🧠 ЛОГИКА: старт движка
    except SystemExit:
        raise               # 🧠 ЛОГИКА: даём sys.exit() завершить программу
    except Exception as e:
        print("ENGINE CRASH:", e)  # 🧠 ЛОГИКА: чтобы видеть причину в консоли
        sys.exit(1)                # 🧠 ЛОГИКА: аварийный выход
