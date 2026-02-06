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
    # ✅ LOADING SCREEN (до тяжёлых импортов)
    # ============================================================
    loader = None
    try:
        from engine.loading_screen import LoadingScreen

        loader = LoadingScreen(title="DragonEngine")
        loader.update(5, "Загрузка…", "Инициализация")
    except Exception:
        loader = None

     # ✅ 3) Импорты движка ПОСЛЕ single-instance
    if loader:
        loader.update(20, "Загрузка…", "Чтение config_engine")

    from engine.config_engine import (  # 🔧 МОЖНО МЕНЯТЬ
        WINDOW_WIDTH,
        WINDOW_HEIGHT,
        WINDOW_TITLE,
        FPS,
        PROJECTS_DIR,
    )

    if loader:
        loader.update(45, "Загрузка…", "Чтение настроек")

    from engine.engine_settings import load_settings  # ✅ НОВОЕ: глобальные настройки

    if loader:
        loader.update(70, "Загрузка…", "Запуск интерфейса")

    from editor.editor_app import run_editor  # 🧠 ЛОГИКА: запуск редактора

    # ✅ 4) Загружаем настройки
    settings = load_settings()

    if loader:
        loader.update(100, "Загрузка…", "Готово")
        loader = None  # просто отпускаем ссылку — окно/pygame НЕ трогаем

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
