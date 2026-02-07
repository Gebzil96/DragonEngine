import sys
import os
from pathlib import Path
from datetime import datetime

# ============================================================
# ✅ SINGLE INSTANCE (Windows Mutex)
# ============================================================
def ensure_single_instance(app_id: str = "DragonEngine.Singleton") -> None:
    """
    🧠 ЛОГИКА:
    Разрешаем запуск ТОЛЬКО одного экземпляра DragonEngine.

    Windows:
    - используем именованный Mutex (самый надёжный способ)

    🔧 МОЖНО МЕНЯТЬ:
    - app_id (лучше не менять без причины)
    """
    if os.name != "nt":
        return  # пока не блокируем Linux/Mac

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32

    kernel32.CreateMutexW.argtypes = [
        wintypes.LPVOID,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    ]
    kernel32.CreateMutexW.restype = wintypes.HANDLE

    kernel32.GetLastError.argtypes = []
    kernel32.GetLastError.restype = wintypes.DWORD

    ERROR_ALREADY_EXISTS = 183

    # ⚠️ ВАЖНО: handle должен жить глобально
    global _DRAGONENGINE_MUTEX_HANDLE  # noqa: PLW0603
    _DRAGONENGINE_MUTEX_HANDLE = kernel32.CreateMutexW(
        None,
        True,
        app_id,
    )

    if not _DRAGONENGINE_MUTEX_HANDLE:
        return

    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        _notify_already_running()
        sys.exit(0)


def _notify_already_running() -> None:
    """
    🧠 ЛОГИКА:
    Уведомление пользователю, что движок уже запущен.
    """
    msg = "DragonEngine уже запущен.\nВторой экземпляр не будет открыт."
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning("DragonEngine", msg)
        try:
            root.destroy()
        except Exception:
            pass
    except Exception:
        print(msg)


# ============================================================
# 🧠 НАСТРОЙКА ЛОГОВ В ФАЙЛ
# ============================================================
def _setup_file_logging() -> None:
    """
    🧠 ЛОГИКА:
    Когда запускаем через pythonw.exe — консоли нет.
    Перенаправляем stdout/stderr в engine_log.txt.

    ✅ ВАЖНО:
    - файл очищается при каждом запуске (mode="w")
    """
    log_path = Path(__file__).resolve().parent / "engine_log.txt"

    # ✅ line-buffered: пишет построчно
    # ✅ mode="w": очищаем лог при каждом запуске движка
    f = open(log_path, "w", encoding="utf-8", buffering=1)

    # ⚠️ ВАЖНО: держим ссылку глобально, чтобы файл точно не закрылся GC
    global _DRAGONENGINE_LOG_FILE  # noqa: PLW0603
    _DRAGONENGINE_LOG_FILE = f

    sys.stdout = f  # type: ignore[assignment]
    sys.stderr = f  # type: ignore[assignment]

    print("\n" + "=" * 60)
    print("DragonEngine старт:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)



# ============================================================
# 🧠 ТОЧКА ВХОДА
# ============================================================
def main():
    """
    🧠 ЛОГИКА: точка входа движка.
    """

    # ✅ 1) СРАЗУ блокируем второй экземпляр (до pygame / UI)
    ensure_single_instance("DragonEngine.Singleton")

    # ✅ 2) Настраиваем логирование
    _setup_file_logging()

    
    # ============================================================
    # ✅ Быстрые импорты ДО LOADER: чтобы сразу выставить правильный режим окна
    # (иначе после 99% будет дерганье при смене set_mode/reinit_display)
    # ============================================================
    settings = {}
    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 720
    WINDOW_TITLE = "DragonEngine"
    FPS = 60
    PROJECTS_DIR = None

    try:
        from engine.config_engine import (  # 🔧 МОЖНО МЕНЯТЬ
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
            WINDOW_TITLE,
            FPS,
            PROJECTS_DIR,
        )
    except Exception:
        pass

    try:
        from engine.engine_settings import load_settings  # ✅ глобальные настройки
        settings = load_settings() or {}
    except Exception:
        settings = {}

    # ============================================================
    # ✅ LOADING SCREEN (до тяжёлых импортов) + "честные проценты"
    # ============================================================
    loader = None
    boot = None
    try:
        from engine.loading_screen import LoadingScreen, BootProgress, BootProgressPlan

        fs = bool(settings.get("fullscreen", False))
        is_max = bool(settings.get("windowed_maximized", False))

        # ✅ если fullscreen: borderless + размер рабочего стола (size=None)
        # ✅ если windowed: обычное окно с рамкой; размер из settings (или дефолты)
        if fs:
            loader = LoadingScreen(title="DragonEngine", size=None, borderless=True)
        else:
            if is_max:
                # окно "на весь экран" (но с рамкой) — берём desktop size через size=None
                loader = LoadingScreen(title="DragonEngine", size=None, borderless=False)
            else:
                ww = int(settings.get("windowed_w", WINDOW_WIDTH))
                wh = int(settings.get("windowed_h", WINDOW_HEIGHT))
                ww = max(320, ww)
                wh = max(240, wh)
                loader = LoadingScreen(title="DragonEngine", size=(ww, wh), borderless=False)

        boot = BootProgress(
            loader,
            plan=BootProgressPlan(
                # 🔧 МОЖНО МЕНЯТЬ: если захочешь подкрутить "ощущение линейности"
                est_imports_s=0.55,
                est_settings_s=0.18,
                est_editor_import_s=0.45,
                est_before_editor_s=0.15,
            ),
            title="Загрузка…",
        )
        boot.ping("Инициализация", floor_pct=1.0)
    except Exception:
        loader = None
        boot = None

    # ✅ 3) Импорты движка ПОСЛЕ single-instance
    if boot:
        boot.ping("Чтение config_engine", floor_pct=2.0)

    from engine.config_engine import (  # 🔧 МОЖНО МЕНЯТЬ
        WINDOW_WIDTH,
        WINDOW_HEIGHT,
        WINDOW_TITLE,
        FPS,
        PROJECTS_DIR,
    )

    if boot:
        boot.ping("Чтение настроек", floor_pct=8.0)

    from engine.engine_settings import load_settings  # ✅ глобальные настройки

    # ✅ 4) Загружаем настройки
    settings = load_settings()

    if boot:
        boot.ping("Запуск интерфейса", floor_pct=15.0)

    from editor.editor_app import run_editor  # 🧠 ЛОГИКА: запуск редактора

    # ВАЖНО:
    # 100% ставим только прямо перед run_editor — чтобы "100%" == "сейчас откроется менеджер"
    if boot:
        # 99% НЕ показываем на отдельном LoadingScreen-окне:
        # именно на стыке "закрываем loader-окно / создаём main window" иногда бывает 1 кадр-миг.
        # 99% и 100% уже рисуются в окне менеджера (см. editor_app.py).
        boot.ping("Открытие менеджера проектов", floor_pct=98.0)
        # освобождаем ссылку; display не трогаем
        loader = None
        boot = None

    # ✅ 5) Запуск редактора
    run_editor(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        window_title=WINDOW_TITLE,
        fps=FPS,
        projects_dir=PROJECTS_DIR,
        fullscreen=bool(settings.get("fullscreen", False)),  # ✅ НОВОЕ
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print("ENGINE CRASH:", e)
        raise
