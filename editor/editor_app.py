import sys
import pygame
import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
from pathlib import Path
import json
import math
import time
import os  # ✅ для подсчёта размера папки + принудительного выхода

# ✅ WinAPI для принудительного возврата фокуса (Windows)
import ctypes
from ctypes import wintypes

# 🧠 ЛОГИКА: путь до engine (где лежат config_engine.py и project_manager.py)
sys.path.append(r"C:\Users\Boris\Desktop\DragonEngine\engine")  # 🔧 МОЖНО МЕНЯТЬ

from config_engine import (
    BUTTON_BG_COLOR,
    BUTTON_BORDER_COLOR,
    BUTTON_BORDER_WIDTH,
    BUTTON_HOVER_COLOR,
    BUTTON_TEXT_COLOR,
    DEFAULT_FONT_SIZE,
    TITLE_FONT_SIZE,
    TITLE_Y,
    TITLE_GAP_Y,
    UI_MARGIN_X,
    EDGE_PAD,
    UI_TOP_Y,
    UI_GAP_X,
    BUTTON_W,
    BUTTON_H,
    ENGINE_VERSION,
    DEFAULT_SCENE_NAME,
    EDITOR_HINT_COLOR,
    EDITOR_BG_COLOR,
    EDITOR_TEXT_COLOR,
)

from project_manager import (
    list_all_projects,
    register_project,
    open_last_project,
    save_last_project,
    open_project_by_path,
    delete_project,
)

from editor.scene_editor import run_scene_editor

from engine_settings import load_settings, save_settings  # ✅ глобальные настройки

# ✅ системная телеметрия (CPU/GPU)
try:
    import psutil  # type: ignore
except Exception:
    psutil = None

try:
    import pynvml  # type: ignore
except Exception:
    pynvml = None


# 🧠 ЛОГИКА: tkinter нужен только для диалогов
root = tk.Tk()
root.withdraw()


# ============================================================
# ✅ ЕДИНЫЙ ЖЁСТКИЙ ВЫХОД (без циклических импортов)
# ============================================================
def force_quit(exit_code: int = 0) -> None:
    """
    🧠 ЛОГИКА:
    Гарантированно завершает процесс Python, чтобы не оставалось "висящих" окон/консолей.

    1) pygame.quit() — корректно закрываем pygame
    2) tkinter root.destroy() — закрываем контекст диалогов
    3) sys.exit() — нормальный выход
    4) os._exit() — жёсткая страховка, если что-то удерживает процесс
    """
    try:
        pygame.quit()
    except Exception:
        pass

    # ⚠️ ПАРАМЕТР (можно менять): пытаться закрыть tkinter при выходе
    CLOSE_TKINTER = True  # 🔧 МОЖНО МЕНЯТЬ

    if CLOSE_TKINTER:
        try:
            r = tk._default_root
            if r is not None:
                r.destroy()
        except Exception:
            pass

    try:
        sys.exit(exit_code)
    except SystemExit:
        os._exit(exit_code)  # 🧨 ГАРАНТИЯ: мгновенно завершаем процесс


class Project:
    """🧠 ЛОГИКА: локальный класс проекта (используется при создании)."""

    def __init__(self, path: Path, name: str):
        self.root = path
        self.name = name
        self.start_scene: Path | None = None

    def set_start_scene(self, scene_path: Path):
        self.start_scene = scene_path


def _draw_lines(screen, font, lines, x, y, color):
    yy = y  # 🔧 МОЖНО МЕНЯТЬ
    for line in lines:
        surf = font.render(line, True, color)
        screen.blit(surf, (x, yy))
        yy += surf.get_height() + 6  # 🔧 МОЖНО МЕНЯТЬ


def _draw_button(screen, font, rect, text, mouse_pos):
    is_hover = rect.collidepoint(mouse_pos)
    bg = BUTTON_HOVER_COLOR if is_hover else BUTTON_BG_COLOR

    pygame.draw.rect(screen, bg, rect)
    pygame.draw.rect(screen, BUTTON_BORDER_COLOR, rect, BUTTON_BORDER_WIDTH)

    label = font.render(text, True, BUTTON_TEXT_COLOR)
    screen.blit(label, label.get_rect(center=rect.center))
    return is_hover


def _draw_exit_button(screen, font, rect, text, mouse_pos):
    """
    🧠 ЛОГИКА:
    Отдельная отрисовка кнопки "Выход", чтобы при наведении она краснела.
    """
    is_hover = rect.collidepoint(mouse_pos)

    EXIT_BG = BUTTON_BG_COLOR  # 🔧 МОЖНО МЕНЯТЬ: обычный фон
    EXIT_HOVER_BG_2 = (180, 55, 55)  # 🔧 МОЖНО МЕНЯТЬ: усиление, когда "сильно красный"

    bg = EXIT_HOVER_BG_2 if is_hover else EXIT_BG

    pygame.draw.rect(screen, bg, rect)
    pygame.draw.rect(screen, BUTTON_BORDER_COLOR, rect, BUTTON_BORDER_WIDTH)

    label = font.render(text, True, BUTTON_TEXT_COLOR)
    screen.blit(label, label.get_rect(center=rect.center))
    return is_hover


def _clamp_int(v: float, lo: int, hi: int) -> int:
    return int(max(lo, min(hi, v)))


def _blend_color(base_rgb: tuple[int, int, int], add_rgb: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    r = _clamp_int(base_rgb[0] + add_rgb[0] * t, 0, 255)
    g = _clamp_int(base_rgb[1] + add_rgb[1] * t, 0, 255)
    b = _clamp_int(base_rgb[2] + add_rgb[2] * t, 0, 255)
    return (r, g, b)


# ============================================================
# ✅ размер папки проекта (в байтах) + красивый формат
# ============================================================
def _get_dir_size_bytes(folder: Path) -> int:
    """
    🧠 ЛОГИКА: суммируем размеры всех файлов в папке (рекурсивно).
    ⚠️ Может быть тяжёлым на огромных папках, поэтому считаем ТОЛЬКО при выборе проекта.
    """
    total = 0
    try:
        for root_dir, _, files in os.walk(folder):
            for fn in files:
                fp = os.path.join(root_dir, fn)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    except Exception:
        return 0
    return total


def _format_bytes(num: int) -> str:
    """
    🧠 ЛОГИКА: человекочитаемый размер (B/KB/MB/GB).
    """
    if num < 0:
        num = 0

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num)
    i = 0
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1

    # 🔧 МОЖНО МЕНЯТЬ: количество знаков после запятой
    if i == 0:
        return f"{int(size)} {units[i]}"
    return f"{size:.2f} {units[i]}"


def check_scene_file(scene_path: Path) -> bool:
    print(f"Проверяем наличие сцены по пути: {scene_path}")
    if scene_path.exists():
        print(f"Сцена найдена: {scene_path}")
        return True
    print(f"Ошибка: Сцена не найдена по пути: {scene_path}")
    return False


def create_scene_file(scene_path: Path):
    scene_data = {
        "name": "MainScene",
        "entities": [],  # 🔧 МОЖНО МЕНЯТЬ
    }
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    with open(scene_path, "w", encoding="utf-8") as scene_file:
        json.dump(scene_data, scene_file, ensure_ascii=False, indent=2)
    print(f"Сцена была успешно создана: {scene_path}")


def create_project(project_dir: Path, project_name: str) -> Project | None:
    if not project_dir.exists():
        project_dir.mkdir(parents=True)

    project_path = project_dir / project_name
    if project_path.exists():
        print(f"Ошибка: Проект с именем '{project_name}' уже существует.")
        return None

    project_path.mkdir(parents=True)

    (project_path / "scenes").mkdir(parents=True, exist_ok=True)
    (project_path / "assets").mkdir(parents=True, exist_ok=True)
    (project_path / "scripts").mkdir(parents=True, exist_ok=True)

    project_json_path = project_path / "project.json"
    project_data = {
        "name": project_name,
        "engine_version": ENGINE_VERSION,
        "start_scene": f"scenes/{DEFAULT_SCENE_NAME}.scene.json",
    }

    with open(project_json_path, "w", encoding="utf-8") as json_file:
        json.dump(project_data, json_file, ensure_ascii=False, indent=2)

    project = Project(project_path, project_name)
    project.set_start_scene(project_path / f"scenes/{DEFAULT_SCENE_NAME}.scene.json")

    if project.start_scene and not project.start_scene.exists():
        create_scene_file(project.start_scene)

    register_project(project.root)
    save_last_project(project.root)

    return project


def open_selected_project() -> Path | None:
    folder = filedialog.askdirectory(title="Выберите папку с проектом")
    if not folder:
        return None
    return Path(folder)


# ============================================================
# ✅ WinAPI: прибиваем окно к (0,0) и нужному размеру (Windows only)
# ============================================================
def _win_force_window_rect(x: int, y: int, w: int, h: int) -> None:
    """
    🧠 ЛОГИКА:
    На Windows SDL иногда "применяет" NOFRAME, но не меняет размер/позицию как надо.
    Поэтому после set_mode() мы добиваем окно через SetWindowPos.
    """
    if sys.platform != "win32":
        return

    try:
        hwnd_raw = pygame.display.get_wm_info().get("window")
        if not hwnd_raw:
            return

        user32 = ctypes.WinDLL("user32", use_last_error=True)

        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        user32.SetWindowPos.argtypes = [
            wintypes.HWND,
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL

        user32.SetWindowPos(
            wintypes.HWND(hwnd_raw),
            None,
            int(x),
            int(y),
            int(w),
            int(h),
            SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )
    except Exception:
        return

# ============================================================
# ✅ WinAPI: вернуть рамку/заголовок после pygame.NOFRAME (Windows only)
# ============================================================
def _win_force_windowed_decorations() -> None:
    """
    🧠 ЛОГИКА:
    После pygame.NOFRAME Windows иногда оставляет стиль WS_POPUP,
    и рамка не возвращается даже если мы сделали set_mode() без NOFRAME.

    Поэтому принудительно переключаем стиль окна на "обычное оконное":
    - убираем WS_POPUP
    - добавляем WS_OVERLAPPEDWINDOW (рамка, заголовок, кнопки, ресайз)
    - делаем SWP_FRAMECHANGED, чтобы Windows пересчитала декорации
    """
    if sys.platform != "win32":
        return

    try:
        hwnd_raw = pygame.display.get_wm_info().get("window")
        if not hwnd_raw:
            return

        user32 = ctypes.WinDLL("user32", use_last_error=True)

        GWL_STYLE = -16
        WS_POPUP = 0x80000000
        WS_OVERLAPPEDWINDOW = 0x00CF0000

        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020

        user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetWindowLongW.restype = ctypes.c_long

        user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        user32.SetWindowLongW.restype = ctypes.c_long

        user32.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_uint,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL

        hwnd = wintypes.HWND(hwnd_raw)
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)

        # ✅ убрать popup-стиль от NOFRAME и вернуть обычные декорации
        style = (style & ~WS_POPUP) | WS_OVERLAPPEDWINDOW
        user32.SetWindowLongW(hwnd, GWL_STYLE, style)

        # ✅ заставить Windows пересчитать рамку/заголовок
        user32.SetWindowPos(
            hwnd, None,
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )
    except Exception:
        pass

# ============================================================
# ✅ WinAPI: max/restore оконного режима (Windows only)
# ============================================================
def _win_is_maximized() -> bool:
    """🧠 ЛОГИКА: True если окно сейчас максимизировано (кнопка '□' нажата)."""
    if sys.platform != "win32":
        return False
    try:
        hwnd_raw = pygame.display.get_wm_info().get("window")
        if not hwnd_raw:
            return False
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.IsZoomed.argtypes = [wintypes.HWND]
        user32.IsZoomed.restype = wintypes.BOOL
        return bool(user32.IsZoomed(wintypes.HWND(hwnd_raw)))
    except Exception:
        return False


def _win_set_maximized(maximize: bool) -> None:
    """🧠 ЛОГИКА: принудительно maximize/restore (чтобы 'оконный на весь экран' был стабильным)."""
    if sys.platform != "win32":
        return
    try:
        hwnd_raw = pygame.display.get_wm_info().get("window")
        if not hwnd_raw:
            return
        user32 = ctypes.WinDLL("user32", use_last_error=True)

        SW_MAXIMIZE = 3
        SW_RESTORE = 9

        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindow.restype = wintypes.BOOL

        user32.ShowWindow(wintypes.HWND(hwnd_raw), SW_MAXIMIZE if maximize else SW_RESTORE)
    except Exception:
        return

# ============================================================
# ✅ ЖЁСТКИЙ ФИКС ФОКУСА ДЛЯ WINDOWS (AttachThreadInput)
# ============================================================
_user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
_SW_RESTORE = 9  # 🔧 МОЖНО МЕНЯТЬ: обычно не трогаем


def _restore_pygame_focus(timeout_sec: float = 1.5) -> None:
    """
    🧠 ЛОГИКА:
    После tkinter-диалогов Windows может не вернуть фокус pygame-окну.
    Тогда первый клик “активирует окно”, второй — настоящий.
    Это лечим через WinAPI + AttachThreadInput.
    """
    pygame.event.clear()
    pygame.event.pump()

    try:
        wm = pygame.display.get_wm_info()
        hwnd_raw = wm.get("window", None)
    except Exception:
        hwnd_raw = None

    if hwnd_raw:
        hwnd = wintypes.HWND(hwnd_raw)

        fg = None
        fg_thread = None
        this_thread = None

        try:
            fg = _user32.GetForegroundWindow()
            fg_thread = _user32.GetWindowThreadProcessId(fg, None)
            this_thread = _user32.GetWindowThreadProcessId(hwnd, None)

            if fg_thread != this_thread:
                _user32.AttachThreadInput(fg_thread, this_thread, True)

            # ✅ ВАЖНО: SW_RESTORE может сбрасывать maximized → окно “усыхает”.
            # Поэтому аккуратно выбираем режим показа.
            SW_MAXIMIZE = 3
            SW_SHOW = 5

            try:
                _user32.IsIconic.argtypes = [wintypes.HWND]
                _user32.IsIconic.restype = wintypes.BOOL
                _user32.IsZoomed.argtypes = [wintypes.HWND]
                _user32.IsZoomed.restype = wintypes.BOOL

                was_minimized = bool(_user32.IsIconic(hwnd))
                was_maximized = bool(_user32.IsZoomed(hwnd))

                if was_minimized:
                    _user32.ShowWindow(hwnd, _SW_RESTORE)
                elif was_maximized:
                    _user32.ShowWindow(hwnd, SW_MAXIMIZE)
                else:
                    _user32.ShowWindow(hwnd, SW_SHOW)
            except Exception:
                # fallback: старое поведение (на всякий случай)
                _user32.ShowWindow(hwnd, _SW_RESTORE)

            _user32.BringWindowToTop(hwnd)
            _user32.SetActiveWindow(hwnd)
            _user32.SetForegroundWindow(hwnd)
            _user32.SetFocus(hwnd)

        finally:
            try:
                if fg_thread is not None and this_thread is not None and fg_thread != this_thread:
                    _user32.AttachThreadInput(fg_thread, this_thread, False)
            except Exception:
                pass

    t0 = time.perf_counter()
    while not pygame.key.get_focused():
        pygame.event.pump()
        if time.perf_counter() - t0 > timeout_sec:
            break
        pygame.time.delay(10)

    t1 = time.perf_counter()
    while pygame.mouse.get_pressed(num_buttons=3)[0]:
        pygame.event.pump()
        if time.perf_counter() - t1 > 0.8:  # 🔧 МОЖНО МЕНЯТЬ
            break
        pygame.time.delay(10)

    pygame.event.clear()
    pygame.event.pump()


# ============================================================
# ✅ ВНУТРЕННЯЯ РЕАЛИЗАЦИЯ
# ============================================================
def _run_editor_impl(
    window_width: int,
    window_height: int,
    window_title: str,
    fps: int,
    projects_dir: Path,
    fullscreen: bool = False,
    
):
    pygame.init()

    # ✅ Настройки движка (persisted) — должны быть загружены ДО любых setdefault()
    engine_settings = load_settings()

    # ✅ fullscreen: берём сохранённое, если есть; иначе — аргумент функции
    fullscreen = bool(engine_settings.get("fullscreen", fullscreen))

    # ✅ Оконный режим "на весь экран" (с рамкой) — запоминаем отдельно
    engine_settings.setdefault("windowed_maximized", False)        # ✅ persisted
    engine_settings.setdefault("windowed_w", int(window_width))    # ✅ persisted
    engine_settings.setdefault("windowed_h", int(window_height))   # ✅ persisted

    # ✅ прочие persisted-настройки
    engine_settings.setdefault("debug_overlay", False)
    engine_settings.setdefault("fullscreen", bool(fullscreen))     # (на всякий случай)

    # ✅ сразу сохраним, чтобы ключи точно появились в файле настроек
    save_settings(engine_settings)

    # ============================================================
    # ✅ ДИСПЛЕЙ-РЕЖИМ (окно / fullscreen)
    # ============================================================
    def _apply_display_mode(fullscreen_on: bool, window_size_override: tuple[int, int] | None = None):
        """🧠 ЛОГИКА:
        Переключаем режим окна.

        Важно:
        - чтобы tkinter окна НЕ сворачивали движок, используем borderless fullscreen (NOFRAME)
        - чтобы borderless реально растягивался при переключении из окна, делаем display.quit/init
        """
        # 🔧 МОЖНО МЕНЯТЬ: True = borderless fullscreen (НЕ сворачивается), False = pygame.FULLSCREEN (может сворачиваться)
        USE_BORDERLESS_FULLSCREEN = True  # 🔧 МОЖНО МЕНЯТЬ

        # 🔧 МОЖНО МЕНЯТЬ: включать RESIZABLE в оконном режиме (если захочешь)
        WINDOW_RESIZABLE = True  # 🔧 МОЖНО МЕНЯТЬ

        if fullscreen_on:
            # ✅ позиция окна (на всякий случай)
            os.environ["SDL_VIDEO_CENTERED"] = "0"
            os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"

            # ✅ КЛЮЧ: переинициализация display, иначе SDL иногда “оставляет” старый размер окна
            try:
                pygame.display.quit()
            except Exception:
                pass
            pygame.display.init()

            info = pygame.display.Info()
            screen_w, screen_h = info.current_w, info.current_h

            if USE_BORDERLESS_FULLSCREEN:
                flags_local = pygame.NOFRAME
                local_screen = pygame.display.set_mode((screen_w, screen_h), flags_local)

                # ✅ добиваем размер/позицию на Windows (если SDL чудит)
                _win_force_window_rect(0, 0, screen_w, screen_h)
            else:
                flags_local = pygame.FULLSCREEN
                local_screen = pygame.display.set_mode((0, 0), flags_local)
                _win_force_window_rect(0, 0, screen_w, screen_h)

            w, h = local_screen.get_size()
            return local_screen, w, h

        # ---- оконный режим ----
        flags_local = 0
        if WINDOW_RESIZABLE:
            flags_local |= pygame.RESIZABLE

        # ✅ КЛЮЧ: после NOFRAME рамка на Windows иногда не возвращается без re-init display
        try:
            pygame.display.quit()
        except Exception:
            pass
        pygame.display.init()

        # ✅ если пришли из fullscreen и хотим НЕ сжимать окно — используем текущий размер
        target_w, target_h = window_width, window_height
        if window_size_override is not None:
            target_w, target_h = window_size_override

        local_screen = pygame.display.set_mode((target_w, target_h), flags_local)

        # ✅ вернуть рамку/заголовок после NOFRAME (Windows)
        _win_force_windowed_decorations()

        w, h = local_screen.get_size()
        return local_screen, w, h

    def _apply_display_from_settings() -> tuple[pygame.Surface, int, int]:
        """
        🧠 ЛОГИКА:
        - fullscreen=True  -> borderless (как сейчас)
        - fullscreen=False -> обычное окно:
            * если windowed_maximized=True -> делаем размером экрана + ShowWindow(MAXIMIZE)
            * иначе -> используем сохранённый windowed_w/windowed_h
        """
        info = pygame.display.Info()
        screen_w, screen_h = info.current_w, info.current_h

        if bool(engine_settings.get("fullscreen", False)):
            return _apply_display_mode(True)

        if bool(engine_settings.get("windowed_maximized", False)):
            s, w, h = _apply_display_mode(False, window_size_override=(screen_w, screen_h))
            _win_set_maximized(True)
            return s, w, h

        ww = int(engine_settings.get("windowed_w", window_width))
        wh = int(engine_settings.get("windowed_h", window_height))
        return _apply_display_mode(False, window_size_override=(ww, wh))

    screen, win_w, win_h = _apply_display_from_settings()

    pygame.display.set_caption(window_title)

    # ✅ clock должен быть всегда, иначе упадём на clock.tick(fps)
    clock = pygame.time.Clock()


    font = pygame.font.SysFont(None, DEFAULT_FONT_SIZE)
    title_font = pygame.font.SysFont(None, TITLE_FONT_SIZE)

    # ============================================================
    # ✅ UX: затемнение + "пауза" при открытии tkinter-окон
    # ============================================================
    def _draw_dim_pause_overlay(text: str = "Открыто окно…") -> None:
        """
        🧠 ЛОГИКА:
        Tkinter-диалоги блокируют главный поток, поэтому мы заранее рисуем "приглушение"
        и делаем flip — экран застывает в этом виде, пока модалка открыта.

        🔧 МОЖНО МЕНЯТЬ:
        - ALPHA: степень затемнения
        - текст и его размер/позицию
        """
        nonlocal screen

        # ✅ актуальные размеры (важно в fullscreen)
        w, h = screen.get_size()

        ALPHA = 150  # 🔧 МОЖНО МЕНЯТЬ: 0..255 (чем больше, тем темнее)
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, ALPHA))
        screen.blit(overlay, (0, 0))

        # ✅ небольшая подсказка в центре
        TEXT_COLOR = (235, 235, 245)  # 🔧 МОЖНО МЕНЯТЬ
        SUB_COLOR = (170, 170, 185)   # 🔧 МОЖНО МЕНЯТЬ

        big = pygame.font.SysFont(None, int(DEFAULT_FONT_SIZE * 1.25))  # 🔧 МОЖНО МЕНЯТЬ
        small = pygame.font.SysFont(None, int(DEFAULT_FONT_SIZE * 0.95))  # 🔧 МОЖНО МЕНЯТЬ

        line1 = big.render(text, True, TEXT_COLOR)
        line2 = small.render("Движок на паузе, пока вы не закроете это окно", True, SUB_COLOR)

        cx, cy = w // 2, h // 2
        screen.blit(line1, line1.get_rect(center=(cx, cy - 10)))
        screen.blit(line2, line2.get_rect(center=(cx, cy + 22)))

        pygame.display.flip()

    def _draw_dim_overlay_only(alpha: int = 110) -> None:
        """
        🧠 ЛОГИКА:
        Затемняет фон, но НЕ рисует текст и НЕ делает flip().
        Используется для внутренних меню (например, "Настройки"), которые не блокируют поток.

        🔧 МОЖНО МЕНЯТЬ:
        - alpha: 0..255 (чем больше — тем темнее)
        """
        nonlocal screen
        w, h = screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(alpha)))
        screen.blit(overlay, (0, 0))

    def _call_modal(fn, *args, overlay_text: str = "Открыто окно…", **kwargs):
        """
        🧠 ЛОГИКА:
        Единая обёртка для любых tkinter модалок:
        1) затемнить+flip
        2) вызвать модалку (она блокирует поток)
        3) восстановить фокус pygame
        """
        _draw_dim_pause_overlay(overlay_text)
        result = fn(*args, **kwargs)
        _restore_pygame_focus()
        return result

    status_message = ""

    title_text = "DragonEngine"

    # 🧠 ЛОГИКА: считаем нижнюю границу заголовка и даём безопасный зазор,
    # чтобы рамка "Менеджер проектов" НЕ наезжала на "DragonEngine" в оконном режиме.
    title_h = title_font.size(title_text)[1]

    HEADER_SAFE_GAP = 10  # 🔧 МОЖНО МЕНЯТЬ: доп. безопасный зазор под заголовком

    # ✅ Важно: рамка панели начинается выше текста менеджера из-за:
    # - mgr_top = manager_y - 8
    # - mgr_panel.y = mgr_top - PANEL_PAD_Y
    # Поэтому добавляем (8 + PANEL_PAD_Y) в расчёт manager_y.
    # 🧠 ЛОГИКА: здесь нельзя ссылаться на PANEL_PAD_Y, т.к. он объявлен ниже в функции
    # (иначе будет UnboundLocalError). Поэтому закладываем его текущую величину (12)
    # + коррекцию "-8" прямо в безопасный зазор.
    HEADER_SAFE_GAP = 30  # 🔧 МОЖНО МЕНЯТЬ: 10 (воздух) + 8 (mgr_top shift) + 12 (PANEL_PAD_Y)

    manager_y = TITLE_Y + title_h + TITLE_GAP_Y + HEADER_SAFE_GAP

    ui_buttons_y = max(UI_TOP_Y, manager_y + font.get_height() + 10)

    # ✅ Кнопка "Выход" — ВЕРХНИЙ ПРАВЫЙ УГОЛ (меньше стандартной)
    EXIT_BTN_W = int(BUTTON_W * 0.72)  # 🔧 МОЖНО МЕНЯТЬ
    EXIT_BTN_H = int(BUTTON_H * 0.78)  # 🔧 МОЖНО МЕНЯТЬ
    EXIT_BTN_MARGIN = EDGE_PAD  # 🔧 МОЖНО МЕНЯТЬ: единый отступ от краёв

    EXIT_BTN_X = win_w - EXIT_BTN_W - EXIT_BTN_MARGIN
    EXIT_BTN_Y = EXIT_BTN_MARGIN
    btn_exit = pygame.Rect(EXIT_BTN_X, EXIT_BTN_Y, EXIT_BTN_W, EXIT_BTN_H)

    # ✅ Настройки движка (persisted)
    # ✅ Настройки движка (persisted) — уже загружены выше
    engine_settings.setdefault("fullscreen", bool(fullscreen))
    engine_settings.setdefault("debug_overlay", False)  # ✅ DEBUG-оверлей (persisted)
     # ✅ состояние окна настроек должно быть всегда определено
    settings_open = False
     # ============================================================
    # ✅ TELEMETRY CACHE (чтобы не дергалось каждый кадр)
    # ============================================================
    telemetry_cpu_smooth: float | None = None
    telemetry_gpu: float | None = None
    telemetry_vram: float | None = None
    telemetry_vram_used_gb: float | None = None
    telemetry_vram_total_gb: float | None = None
    telemetry_ram_used_gb: float | None = None
    telemetry_ram_total_gb: float | None = None
    telemetry_ram_pct: float | None = None
    telemetry_frame_ms_smooth: float | None = None

    TELEMETRY_UPDATE_MS = 500  # 🔧 МОЖНО МЕНЯТЬ: как часто обновлять значения (мс)
    CPU_SMOOTH_ALPHA = 0.20    # 🔧 МОЖНО МЕНЯТЬ: 0..1 (меньше = более плавно)
    last_telemetry_update = 0
    # ============================================================
    # ✅ КНОПКИ МЕНЕДЖЕРА ПРОЕКТОВ
    # ============================================================
    btn_create = pygame.Rect(UI_MARGIN_X, ui_buttons_y, BUTTON_W, BUTTON_H)
    btn_last_project = pygame.Rect(UI_MARGIN_X + BUTTON_W + UI_GAP_X, ui_buttons_y, BUTTON_W, BUTTON_H)
    btn_open_project = pygame.Rect(UI_MARGIN_X, ui_buttons_y + BUTTON_H + UI_GAP_X, BUTTON_W, BUTTON_H)

    # ============================================================
    # ✅ Кнопка "Настройки"
    # ============================================================
    SETTINGS_BTN_W = int(BUTTON_W * 0.72)  # 🔧 МОЖНО МЕНЯТЬ
    SETTINGS_BTN_H = int(BUTTON_H * 0.78)  # 🔧 МОЖНО МЕНЯТЬ
    SETTINGS_BTN_X = EDGE_PAD  # 🔧 МОЖНО МЕНЯТЬ: единый отступ от краёв
    SETTINGS_BTN_Y = EXIT_BTN_Y

    btn_settings = pygame.Rect(SETTINGS_BTN_X, SETTINGS_BTN_Y, SETTINGS_BTN_W, SETTINGS_BTN_H)

    def _update_exit_button() -> None:
        nonlocal EXIT_BTN_X, EXIT_BTN_Y
        EXIT_BTN_X = win_w - EXIT_BTN_W - EXIT_BTN_MARGIN
        EXIT_BTN_Y = EXIT_BTN_MARGIN
        btn_exit.x = EXIT_BTN_X
        btn_exit.y = EXIT_BTN_Y
        btn_settings.y = EXIT_BTN_Y

    selected_project_index: int | None = None

    selected_project_path_text: str = ""
    selected_project_size_text: str = ""
    selected_project_cached_root: Path | None = None

    last_click_time = 0
    last_click_index: int | None = None
    DOUBLE_CLICK_MS = 350  # 🔧 МОЖНО МЕНЯТЬ

    PROJECT_LIST_X = UI_MARGIN_X  # 🔧 МОЖНО МЕНЯТЬ
    PROJECT_LIST_Y = 0  # 🧠 вычисляется динамически ниже
    PROJECT_ITEM_W = 420  # 🔧 МОЖНО МЕНЯТЬ
    PROJECT_ITEM_H = 36  # 🔧 МОЖНО МЕНЯТЬ
    PROJECT_ITEM_GAP = 8  # 🔧 МОЖНО МЕНЯТЬ

    # ============================================================
    # ✅ UI PANELS (рамочки как у debug overlay)
    # ============================================================
    PANEL_PAD_X = 14            # 🔧 МОЖНО МЕНЯТЬ: внутренний отступ панели по X
    PANEL_PAD_Y = 12            # 🔧 МОЖНО МЕНЯТЬ: внутренний отступ панели по Y
    PANEL_RADIUS = 10           # 🔧 МОЖНО МЕНЯТЬ: скругление углов
    PANEL_BG_COLOR = (28, 30, 40)      # 🔧 МОЖНО МЕНЯТЬ: холодный тёмно-синий (отделяет от серых кнопок)
    PANEL_BG_ALPHA = 235              # 🔧 МОЖНО МЕНЯТЬ: почти непрозрачно → чёткая карточка
    PANEL_BORDER_COLOR = (170, 180, 220)  # 🔧 МОЖНО МЕНЯТЬ: светлая холодная рамка
    PANEL_BORDER_W = 1
    PANELS_GAP_Y = 14  # 🔧 МОЖНО МЕНЯТЬ: расстояние между панелью менеджера и списком
    PROJECTS_TITLE_OFFSET_Y = 30  # 🔧 МОЖНО МЕНЯТЬ: на сколько заголовок "Проекты:" выше списка
    PROJECTS_TITLE_TOP_PAD = 6    # 🔧 МОЖНО МЕНЯТЬ: небольшой верхний зазор внутри панели списка

    def _draw_panel(rect: pygame.Rect) -> None:
        """🧠 ЛОГИКА: рисуем полупрозрачную панель + рамку (как debug overlay)."""
        overlay = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        overlay.fill((*PANEL_BG_COLOR, int(PANEL_BG_ALPHA)))
        screen.blit(overlay, (rect.x, rect.y))
        pygame.draw.rect(screen, PANEL_BORDER_COLOR, rect, PANEL_BORDER_W, border_radius=PANEL_RADIUS)

    # ✅ Hover-подсветка элемента списка проектов
    PROJECT_ITEM_BG = (40, 40, 46)          # 🔧 МОЖНО МЕНЯТЬ: обычный фон (у тебя он уже используется)
    PROJECT_ITEM_SELECTED_BG = (70, 100, 160)  # 🔧 МОЖНО МЕНЯТЬ: выбранный проект (у тебя он уже используется)

    PROJECT_ITEM_HOVER_BG = (55, 55, 70)    # 🔧 МОЖНО МЕНЯТЬ: фон при наведении (hover)
    PROJECT_ITEM_HOVER_BORDER = (120, 120, 150)  # 🔧 МОЖНО МЕНЯТЬ: обводка hover
    PROJECT_ITEM_HOVER_BORDER_W = 2         # 🔧 МОЖНО МЕНЯТЬ: толщина обводки

    # ✅ Пульсация кнопок
    DELETE_PULSE_SPEED = 3.2  # 🔧 МОЖНО МЕНЯТЬ
    DELETE_PULSE_ADD = (90, 30, 30)  # 🔧 МОЖНО МЕНЯТЬ

    OPEN_PULSE_SPEED = 2.6  # 🔧 МОЖНО МЕНЯТЬ
    OPEN_PULSE_ADD = (30, 60, 90)  # 🔧 МОЖНО МЕНЯТЬ

    # ✅ компактные кнопки для выбранного проекта (в ряд)
    SELECTED_BUTTON_GAP_X = 10  # 🔧 МОЖНО МЕНЯТЬ
    SELECTED_BUTTON_MIN_W = 120  # 🔧 МОЖНО МЕНЯТЬ
    SELECTED_BUTTON_MAX_W = 220  # 🔧 МОЖНО МЕНЯТЬ
    SELECTED_BUTTON_H = 32  # 🔧 МОЖНО МЕНЯТЬ
    SELECTED_BUTTON_W_SCALE = 0.20  # 🔧 МОЖНО МЕНЯТЬ: 0.5 = в 2 раза короче

    BOTTOM_SAFE_PAD = 18  # 🔧 МОЖНО МЕНЯТЬ
    STATUS_GAP = 10  # 🔧 МОЖНО МЕНЯТЬ

    def _selected_buttons_panel_x() -> int:
        return UI_MARGIN_X + PROJECT_ITEM_W + UI_GAP_X

    def _selected_button_width() -> int:
        panel_x = _selected_buttons_panel_x()
        available = win_w - panel_x - UI_MARGIN_X
        w = int((available - SELECTED_BUTTON_GAP_X) / 2)

        # ✅ делаем кнопки короче (по запросу — в 2 раза)
        w = int(w * SELECTED_BUTTON_W_SCALE)

        w = max(SELECTED_BUTTON_MIN_W, min(SELECTED_BUTTON_MAX_W, w))
        return w

    def _selected_button_y_for_item(item_y: int) -> int:
        return item_y + max(0, (PROJECT_ITEM_H - SELECTED_BUTTON_H) // 2)

    def _get_open_selected_button_rect(selected_index: int) -> pygame.Rect:
        item_y = PROJECT_LIST_Y + selected_index * (PROJECT_ITEM_H + PROJECT_ITEM_GAP)
        y = _selected_button_y_for_item(item_y)
        w = _selected_button_width()
        x = _selected_buttons_panel_x()
        return pygame.Rect(x, y, w, SELECTED_BUTTON_H)

    def _get_delete_button_rect(selected_index: int) -> pygame.Rect:
        open_rect = _get_open_selected_button_rect(selected_index)
        w = open_rect.width
        x = open_rect.x + w + SELECTED_BUTTON_GAP_X
        return pygame.Rect(x, open_rect.y, w, SELECTED_BUTTON_H)

    armed_action: str | None = None

    def _update_selected_project_info(info) -> None:
        nonlocal selected_project_path_text, selected_project_size_text, selected_project_cached_root

        root_path = info.root.resolve()
        if selected_project_cached_root == root_path:
            return

        selected_project_cached_root = root_path
        selected_project_path_text = str(root_path)

        size_bytes = _get_dir_size_bytes(root_path)
        selected_project_size_text = _format_bytes(size_bytes)
    # ============================================================
    # ✅ DEBUG TELEMETRY: CPU/GPU/VRAM (best-effort)
    # ============================================================

    _NVML_READY = False

    def _telemetry_init_once() -> None:
        """🧠 ЛОГИКА: инициализируем NVML один раз (если доступно)."""
        nonlocal _NVML_READY
        if _NVML_READY:
            return

        if pynvml is None:
            return

        try:
            pynvml.nvmlInit()
            _NVML_READY = True
        except Exception:
            _NVML_READY = False
    
    def _get_ram_metrics() -> tuple[float | None, float | None, float | None]:
        """
        🧠 ЛОГИКА:
        Возвращаем:
        - RAM used (GB)
        - RAM total (GB)
        - RAM used (%)
        """
        if psutil is None:
            return (None, None, None)

        try:
            vm = psutil.virtual_memory()
            GB = 1024.0 ** 3
            used_gb = float(vm.used) / GB
            total_gb = float(vm.total) / GB
            pct = float(vm.percent)
            return (used_gb, total_gb, pct)
        except Exception:
            return (None, None, None)

    def _get_cpu_percent() -> float | None:
        """🧠 ЛОГИКА: CPU load в процентах (0..100)."""
        if psutil is None:
            return None
        try:
            # interval=None -> моментальная оценка (psutil сам усредняет между вызовами)
            return float(psutil.cpu_percent(interval=None))
        except Exception:
            return None


    def _get_nvidia_gpu_metrics() -> tuple[float | None, float | None, float | None, float | None]:
        """
        🧠 ЛОГИКА:
        Возвращаем:
        - GPU load (%) 0..100
        - VRAM used (%) 0..100
        - VRAM used (GB)
        - VRAM total (GB)

        Только для NVIDIA (NVML). Если NVML не доступна -> (None, None, None, None)
        """
        _telemetry_init_once()
        if not _NVML_READY or pynvml is None:
            return (None, None, None, None)

        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # 🔧 МОЖНО МЕНЯТЬ: GPU #0
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)

            gpu_load = float(util.gpu)  # %

            used = float(mem.used)
            total = float(mem.total)

            vram_used_pct = (used / total * 100.0) if total > 0 else 0.0

            GB = 1024.0 ** 3
            used_gb = used / GB
            total_gb = total / GB

            return (gpu_load, vram_used_pct, used_gb, total_gb)
        except Exception:
            return (None, None, None, None)


    def _clear_selected_project_info() -> None:
        nonlocal selected_project_path_text, selected_project_size_text, selected_project_cached_root
        selected_project_path_text = ""
        selected_project_size_text = ""
        selected_project_cached_root = None

    # ============================================================
    # ✅ Запуск сцены + возврат в менеджер
    # ============================================================
    def _launch_scene(scene_path: Path) -> None:
        nonlocal screen, status_message, win_w, win_h, fullscreen

        # ============================================================
        # ✅ Перед запуском редактора сцены: фиксируем текущее состояние окна в persisted settings
        # ============================================================
        try:
            cur_w, cur_h = screen.get_size()
            engine_settings["fullscreen"] = bool(fullscreen)

            # если сейчас НЕ fullscreen — сохраняем “оконный” размер и maximize-флаг
            if not bool(fullscreen):
                # 🧠 ЛОГИКА: если у тебя уже есть _win_is_maximized() — используй его; иначе считаем False
                is_max = False
                try:
                    is_max = bool(_win_is_maximized())  # type: ignore[name-defined]
                except Exception:
                    is_max = False

                engine_settings["windowed_maximized"] = bool(is_max)

                # ✅ если не maximized — сохраняем нормальный размер
                if not is_max:
                    engine_settings["windowed_w"] = int(cur_w)
                    engine_settings["windowed_h"] = int(cur_h)

            save_settings(engine_settings)
        except Exception:
            pass


        result = run_scene_editor(scene_path, win_w, win_h, fps)

        if result == "quit":
            force_quit(0)

        pygame.display.set_caption(window_title)

        # ✅ ВАЖНО: редактор сцены мог поменять fullscreen/windowed_maximized/размер — перечитываем settings
        engine_settings.update(load_settings())

        # ✅ ВАЖНО: применяем режим 1:1 как при старте менеджера (учитывает windowed_maximized + windowed_w/h)
        screen, win_w, win_h = _apply_display_from_settings()
        fullscreen = bool(engine_settings.get("fullscreen", False))

        _update_exit_button()

        pygame.event.clear()
        pygame.event.pump()

        status_message = "Возврат в менеджер проектов."

    # ============================================================
    # ✅ ДЕЙСТВИЯ КНОПОК (обёртка modal добавлена)
    # ============================================================
    def _do_create():
        nonlocal status_message

        project_location = _call_modal(
            filedialog.askdirectory,
            title="Выберите папку для проекта",
            overlay_text="Выбор папки…",
        )

        if project_location:
            project_name = _call_modal(
                simpledialog.askstring,
                "Имя проекта",
                "Введите имя проекта:",
                overlay_text="Ввод имени проекта…",
            )

            if project_name:
                created = create_project(Path(project_location), project_name)
                if created is None:
                    status_message = "Ошибка: проект уже существует."
                else:
                    status_message = f"Проект '{created.name}' создан."
                    print(f"Открытие стартовой сцены: {created.start_scene}")

                    if created.start_scene and check_scene_file(created.start_scene):
                        _launch_scene(created.start_scene)

    def _do_last():
        nonlocal status_message
        print("Клик по кнопке 'Последний проект'")
        info = open_last_project(projects_dir)
        if info is None:
            status_message = "Последний проект не найден."
        else:
            status_message = f"Открываем: {info.name}"
            print(f"Стартовая сцена: {info.start_scene}")

            register_project(info.root)
            save_last_project(info.root)

            if check_scene_file(info.start_scene):
                _launch_scene(info.start_scene)

    def _do_open():
        nonlocal status_message
        print("Клик по кнопке 'Открыть проект'")

        project_root = _call_modal(
            filedialog.askdirectory,
            title="Выберите папку с проектом",
            overlay_text="Выбор проекта…",
        )

        if project_root:
            info = open_project_by_path(Path(project_root))
            if info is None:
                status_message = "Ошибка: project.json не найден в выбранной папке."
            else:
                status_message = f"Проект '{info.name}' открыт."

                register_project(info.root)
                save_last_project(info.root)

                if check_scene_file(info.start_scene):
                    _launch_scene(info.start_scene)

    def _do_open_selected():
        nonlocal status_message
        if selected_project_index is None:
            return

        all_projects_local = list_all_projects()
        if not (0 <= selected_project_index < len(all_projects_local)):
            return

        info = all_projects_local[selected_project_index]
        status_message = f"Открываем: {info.name}"

        register_project(info.root)
        save_last_project(info.root)

        if check_scene_file(info.start_scene):
            _launch_scene(info.start_scene)

    def _do_delete():
        nonlocal status_message, selected_project_index, last_click_index, last_click_time
        if selected_project_index is None:
            return

        all_projects_local = list_all_projects()
        if not (0 <= selected_project_index < len(all_projects_local)):
            return

        info = all_projects_local[selected_project_index]

        confirm = _call_modal(
            messagebox.askyesno,
            "Удаление проекта",
            f"Удалить проект '{info.name}'?\n\nПапка будет удалена полностью:\n{info.root}",
            overlay_text="Подтверждение удаления…",
        )

        if confirm:
            ok = delete_project(info.root)
            if ok:
                status_message = f"Проект '{info.name}' удалён."
                selected_project_index = None
                last_click_index = None
                last_click_time = 0
                _clear_selected_project_info()
            else:
                status_message = "Ошибка: проект не найден для удаления."
        else:
            status_message = "Удаление отменено."

    def _confirm_exit() -> bool:
        confirm_exit = _call_modal(
            messagebox.askyesno,
            "Выход",
            "Вы действительно хотите выйти?",
            overlay_text="Подтверждение выхода…",
        )
        return bool(confirm_exit)

    # ============================================================
    # ✅ UI: вычисление rect панели настроек (единое место)
    # ============================================================
    def _settings_panel_rect() -> pygame.Rect:
        PANEL_W = 280  # 🔧 МОЖНО МЕНЯТЬ
        PANEL_H = 140   # 🔧 МОЖНО МЕНЯТЬ
        PANEL_MARGIN_Y = 6  # 🔧 МОЖНО МЕНЯТЬ

        panel_x = btn_settings.x
        panel_y = btn_settings.bottom + PANEL_MARGIN_Y
        return pygame.Rect(panel_x, panel_y, PANEL_W, PANEL_H)

    def _settings_checkbox_debug_rect(panel_rect: pygame.Rect) -> pygame.Rect:
        # ✅ второй чекбокс ниже fullscreen
        return pygame.Rect(panel_rect.x + 12, panel_rect.y + 80, 20, 20)
    
    def _settings_checkbox_fullscreen_rect(panel_rect: pygame.Rect) -> pygame.Rect:
        # ✅ чекбокс полноэкранного режима
        return pygame.Rect(panel_rect.x + 12, panel_rect.y + 44, 20, 20)

    # ============================================================
    # ✅ WINDOW STATE CACHE (чтобы запоминать maximize/размер)
    # ============================================================
    WINDOW_STATE_SAVE_MS = 800  # 🔧 МОЖНО МЕНЯТЬ
    last_window_state_save = 0

    running = True
    while running:
        clock.tick(fps)
        mouse_pos = pygame.mouse.get_pos()

        win_w, win_h = screen.get_size()
        _update_exit_button()

        # ✅ Запоминаем "оконный на весь экран" и размеры (только когда fullscreen выключен)
        now_ms = pygame.time.get_ticks()
        if (not bool(engine_settings.get("fullscreen", False))) and (now_ms - last_window_state_save >= WINDOW_STATE_SAVE_MS):
            last_window_state_save = now_ms

            is_max = _win_is_maximized()
            cur_w, cur_h = screen.get_size()

            changed = False

            if bool(engine_settings.get("windowed_maximized", False)) != bool(is_max):
                engine_settings["windowed_maximized"] = bool(is_max)
                changed = True

            # ✅ если не максимизировано — запоминаем “нормальный” размер
            if not is_max:
                if int(engine_settings.get("windowed_w", 0)) != int(cur_w):
                    engine_settings["windowed_w"] = int(cur_w)
                    changed = True
                if int(engine_settings.get("windowed_h", 0)) != int(cur_h):
                    engine_settings["windowed_h"] = int(cur_h)
                    changed = True

            if changed:
                save_settings(engine_settings)


        if not pygame.mouse.get_pressed(num_buttons=3)[0]:
            armed_action = None

        all_projects = list_all_projects()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if _confirm_exit():
                    force_quit(0)
                else:
                    continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos

                if btn_exit.collidepoint(pos):
                    armed_action = "exit"
                    continue

                if btn_settings.collidepoint(pos):
                    armed_action = "settings"
                    continue

                if settings_open:
                    panel_rect = _settings_panel_rect()
                    if panel_rect.collidepoint(pos):
                        armed_action = "settings_panel"
                    else:
                        armed_action = "settings_outside"
                    continue

                if btn_create.collidepoint(pos):
                    armed_action = "create"
                    continue
                if btn_last_project.collidepoint(pos):
                    armed_action = "last"
                    continue
                if btn_open_project.collidepoint(pos):
                    armed_action = "open"
                    continue

                if selected_project_index is not None and 0 <= selected_project_index < len(all_projects):
                    open_sel_rect = _get_open_selected_button_rect(selected_project_index)
                    if open_sel_rect.collidepoint(pos):
                        armed_action = "open_selected"
                        continue

                    delete_rect = _get_delete_button_rect(selected_project_index)
                    if delete_rect.collidepoint(pos):
                        armed_action = "delete"
                        continue

                clicked_index: int | None = None
                y = PROJECT_LIST_Y
                for i, p in enumerate(all_projects):
                    item_rect = pygame.Rect(PROJECT_LIST_X, y, PROJECT_ITEM_W, PROJECT_ITEM_H)
                    if item_rect.collidepoint(pos):
                        clicked_index = i
                        break
                    y += PROJECT_ITEM_H + PROJECT_ITEM_GAP

                if clicked_index is not None:
                    selected_project_index = clicked_index

                    try:
                        info_for_selected = all_projects[clicked_index]
                        _update_selected_project_info(info_for_selected)
                    except Exception:
                        _clear_selected_project_info()

                    now_ms = pygame.time.get_ticks()
                    is_double_click = last_click_index == clicked_index and (now_ms - last_click_time) <= DOUBLE_CLICK_MS
                    last_click_index = clicked_index
                    last_click_time = now_ms

                    if is_double_click:
                        info = all_projects[clicked_index]
                        register_project(info.root)
                        save_last_project(info.root)

                        if check_scene_file(info.start_scene):
                            _launch_scene(info.start_scene)
                else:
                    selected_project_index = None
                    last_click_index = None
                    last_click_time = 0
                    _clear_selected_project_info()

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                pos = event.pos

                if armed_action == "exit" and btn_exit.collidepoint(pos):
                    if _confirm_exit():
                        force_quit(0)

                elif armed_action == "settings" and btn_settings.collidepoint(pos):
                    settings_open = not settings_open

                elif settings_open:
                    panel_rect = _settings_panel_rect()
                    checkbox_rect = _settings_checkbox_fullscreen_rect(panel_rect)
                    debug_rect = _settings_checkbox_debug_rect(panel_rect)

                    if checkbox_rect.collidepoint(pos):
                        # ✅ запоминаем текущий размер ДО переключения
                        cur_w, cur_h = screen.get_size()

                        engine_settings["fullscreen"] = not bool(engine_settings.get("fullscreen", False))
                        save_settings(engine_settings)

                        fullscreen = bool(engine_settings["fullscreen"])

                        # ✅ Важно: при выключении fullscreen НЕ сжимаем окно — оставляем текущий размер, но с рамкой
                        if not fullscreen:
                            # ✅ считаем это "оконный на весь экран" (с рамкой), и запоминаем
                            engine_settings["windowed_maximized"] = True
                            engine_settings["windowed_w"] = int(cur_w)
                            engine_settings["windowed_h"] = int(cur_h)
                            save_settings(engine_settings)

                            screen, win_w, win_h = _apply_display_from_settings()
                        else:
                            screen, win_w, win_h = _apply_display_mode(True)

                        _update_exit_button()

                        pygame.display.set_caption(window_title)
                        pygame.event.clear()

                    elif debug_rect.collidepoint(pos):
                        engine_settings["debug_overlay"] = not bool(engine_settings.get("debug_overlay", False))
                        save_settings(engine_settings)
                    
                      # ✅ если включили debug — форсим обновление телеметрии на следующем кадре
                        if engine_settings.get("debug_overlay", False):
                            last_telemetry_update = -10_000  # ✅ гарантированный refresh

                    elif not panel_rect.collidepoint(pos) and not btn_settings.collidepoint(pos):
                        settings_open = False

                elif armed_action == "create" and btn_create.collidepoint(pos):
                    _do_create()
                elif armed_action == "last" and btn_last_project.collidepoint(pos):
                    _do_last()
                elif armed_action == "open" and btn_open_project.collidepoint(pos):
                    _do_open()
                elif armed_action == "open_selected":
                    if selected_project_index is not None and 0 <= selected_project_index < len(all_projects):
                        open_sel_rect = _get_open_selected_button_rect(selected_project_index)
                        if open_sel_rect.collidepoint(pos):
                            _do_open_selected()
                elif armed_action == "delete":
                    if selected_project_index is not None and 0 <= selected_project_index < len(all_projects):
                        delete_rect = _get_delete_button_rect(selected_project_index)
                        if delete_rect.collidepoint(pos):
                            _do_delete()

                armed_action = None

        # --- РЕНДЕР ---
        screen.fill(EDITOR_BG_COLOR)

        _draw_exit_button(screen, font, btn_exit, "Выход", mouse_pos)
        _draw_button(screen, font, btn_settings, "Настройки", mouse_pos)

        title_w = title_font.size(title_text)[0]
        title_x = (win_w - title_w) // 2
        screen.blit(title_font.render(title_text, True, EDITOR_TEXT_COLOR), (title_x, TITLE_Y))

        # ✅ Панель: "Менеджер проектов" + его кнопки
        mgr_left = UI_MARGIN_X
        mgr_top = manager_y - 8  # 🔧 МОЖНО МЕНЯТЬ: чуть выше заголовка
        mgr_right = max(btn_create.right, btn_last_project.right, btn_open_project.right)
        mgr_bottom = max(btn_create.bottom, btn_last_project.bottom, btn_open_project.bottom)

        mgr_panel = pygame.Rect(
            mgr_left - PANEL_PAD_X,
            mgr_top - PANEL_PAD_Y,
            (mgr_right - mgr_left) + PANEL_PAD_X * 2,
            (mgr_bottom - mgr_top) + PANEL_PAD_Y * 2,
        )
        _draw_panel(mgr_panel)

         # 🧠 ЛОГИКА: учитываем, что панель списка начинается выше PROJECT_LIST_Y из-за заголовка
        PROJECT_LIST_Y = (
            mgr_panel.bottom
            + PANELS_GAP_Y
            + PROJECTS_TITLE_OFFSET_Y
            + PROJECTS_TITLE_TOP_PAD
            + PANEL_PAD_Y
        )

        screen.blit(font.render("Менеджер проектов:", True, EDITOR_TEXT_COLOR), (UI_MARGIN_X, manager_y))

        _draw_button(screen, font, btn_create, "Создать проект", mouse_pos)
        _draw_button(screen, font, btn_last_project, "Последний проект", mouse_pos)
        _draw_button(screen, font, btn_open_project, "Открыть проект", mouse_pos)

         # ✅ Панель: список проектов (заголовок + список + кнопки справа)
        list_left = PROJECT_LIST_X
        list_top = (PROJECT_LIST_Y - PROJECTS_TITLE_OFFSET_Y) - PROJECTS_TITLE_TOP_PAD
        list_count = max(1, len(all_projects))
        list_h = list_count * PROJECT_ITEM_H + (list_count - 1) * PROJECT_ITEM_GAP

        # ширина: список + (если есть) зона кнопок выбранного проекта
        list_right = PROJECT_LIST_X + PROJECT_ITEM_W
        if selected_project_index is not None and 0 <= selected_project_index < len(all_projects):
            # включаем правые кнопки в панель
            list_right = max(list_right, _get_delete_button_rect(selected_project_index).right)

        list_bottom = PROJECT_LIST_Y + list_h

        list_panel = pygame.Rect(
            list_left - PANEL_PAD_X,
            list_top - PANEL_PAD_Y,
            (list_right - list_left) + PANEL_PAD_X * 2,
            (list_bottom - list_top) + PANEL_PAD_Y * 2,
        )
        _draw_panel(list_panel)

        screen.blit(
            font.render("Проекты:", True, EDITOR_TEXT_COLOR),
            (UI_MARGIN_X, PROJECT_LIST_Y - PROJECTS_TITLE_OFFSET_Y),
        )

        y = PROJECT_LIST_Y
        if all_projects:
            for i, p in enumerate(all_projects):
                item_rect = pygame.Rect(PROJECT_LIST_X, y, PROJECT_ITEM_W, PROJECT_ITEM_H)

                # 🧠 ЛОГИКА: hover считается каждый кадр (стабильно, без залипаний)
                is_hover = item_rect.collidepoint(mouse_pos)

                # 🧠 ЛОГИКА: фон элемента списка
                if selected_project_index == i:
                    bg = PROJECT_ITEM_SELECTED_BG
                elif is_hover:
                    bg = PROJECT_ITEM_HOVER_BG
                else:
                    bg = PROJECT_ITEM_BG

                pygame.draw.rect(screen, bg, item_rect)

                # ✅ обводка hover (чтобы было прям очевидно “куда навёл”)
                if (selected_project_index != i) and is_hover:
                    pygame.draw.rect(
                        screen,
                        PROJECT_ITEM_HOVER_BORDER,
                        item_rect,
                        PROJECT_ITEM_HOVER_BORDER_W,
                    )

                pygame.draw.rect(screen, BUTTON_BORDER_COLOR, item_rect, 1)
                screen.blit(font.render(p.name, True, EDITOR_TEXT_COLOR), (item_rect.x + 10, item_rect.y + 6))

                y += PROJECT_ITEM_H + PROJECT_ITEM_GAP
        else:
            _draw_lines(screen, font, ["(пока пусто)"], x=PROJECT_LIST_X, y=PROJECT_LIST_Y, color=EDITOR_TEXT_COLOR)

        if selected_project_index is not None and 0 <= selected_project_index < len(all_projects):
            open_sel_rect = _get_open_selected_button_rect(selected_project_index)
            delete_rect = _get_delete_button_rect(selected_project_index)

            t = pygame.time.get_ticks() / 1000.0

            pulse_open = (math.sin(t * OPEN_PULSE_SPEED) + 1.0) * 0.5
            open_bg = _blend_color(BUTTON_BG_COLOR, OPEN_PULSE_ADD, pulse_open)
            if open_sel_rect.collidepoint(mouse_pos):
                open_bg = _blend_color(open_bg, (20, 30, 40), 1.0)  # 🔧 МОЖНО МЕНЯТЬ

            pygame.draw.rect(screen, open_bg, open_sel_rect)
            pygame.draw.rect(screen, BUTTON_BORDER_COLOR, open_sel_rect, BUTTON_BORDER_WIDTH)
            label_open = font.render("Открыть", True, BUTTON_TEXT_COLOR)  # 🔧 МОЖНО МЕНЯТЬ
            screen.blit(label_open, label_open.get_rect(center=open_sel_rect.center))

            pulse_del = (math.sin(t * DELETE_PULSE_SPEED) + 1.0) * 0.5
            del_bg = _blend_color(BUTTON_BG_COLOR, DELETE_PULSE_ADD, pulse_del)
            if delete_rect.collidepoint(mouse_pos):
                del_bg = _blend_color(del_bg, (50, 20, 20), 1.0)  # 🔧 МОЖНО МЕНЯТЬ

            pygame.draw.rect(screen, del_bg, delete_rect)
            pygame.draw.rect(screen, BUTTON_BORDER_COLOR, delete_rect, BUTTON_BORDER_WIDTH)
            label_del = font.render("Удалить", True, BUTTON_TEXT_COLOR)  # 🔧 МОЖНО МЕНЯТЬ
            screen.blit(label_del, label_del.get_rect(center=delete_rect.center))

        line_h = font.get_height() + 6
        info_lines_count = 0

        if selected_project_index is not None and selected_project_path_text:
            info_lines_count = 3

        status_lines_count = 1 if status_message else 0

        status_y = win_h - BOTTOM_SAFE_PAD - (status_lines_count * line_h)  # 🔧 МОЖНО МЕНЯТЬ
        info_y = status_y - (STATUS_GAP + (info_lines_count * line_h))  # 🔧 МОЖНО МЕНЯТЬ

        if info_lines_count > 0:
            info_lines = [
                "Выбранный проект:",
                f"Путь: {selected_project_path_text}",
                f"Размер: {selected_project_size_text}",
            ]
            _draw_lines(screen, font, info_lines, x=UI_MARGIN_X, y=info_y, color=EDITOR_HINT_COLOR)

        if status_message:
            _draw_lines(screen, font, [status_message], x=UI_MARGIN_X, y=status_y, color=EDITOR_HINT_COLOR)

        # ============================================================
        # ✅ DEBUG-OVERLAY (справа сверху + полупрозрачный фон)
        # ============================================================
        if engine_settings.get("debug_overlay", False):

            now_ms = pygame.time.get_ticks()

            # ✅ обновляем телеметрию:
            # - по таймеру
            # - ИЛИ если GPU/VRAM ещё не заполнены (иначе будет N/A после toggle)
            need_refresh = (now_ms - last_telemetry_update >= TELEMETRY_UPDATE_MS)
            need_refresh = need_refresh or (telemetry_gpu is None) or (telemetry_vram is None)

            if need_refresh:
                last_telemetry_update = now_ms

                cpu_raw = _get_cpu_percent()
                # ====================================================
                # ✅ CPU smoothing (EMA) — фикс дерганья
                # ====================================================
                if cpu_raw is not None:
                    if telemetry_cpu_smooth is None:
                        telemetry_cpu_smooth = float(cpu_raw)
                    else:
                        telemetry_cpu_smooth = (
                            telemetry_cpu_smooth * (1.0 - CPU_SMOOTH_ALPHA)
                            + float(cpu_raw) * CPU_SMOOTH_ALPHA
                        )
                gpu_raw, vram_pct_raw, vram_used_gb_raw, vram_total_gb_raw = _get_nvidia_gpu_metrics()

                ram_used_gb_raw, ram_total_gb_raw, ram_pct_raw = _get_ram_metrics()

                if ram_used_gb_raw is not None:
                    telemetry_ram_used_gb = ram_used_gb_raw
                if ram_total_gb_raw is not None:
                    telemetry_ram_total_gb = ram_total_gb_raw
                if ram_pct_raw is not None:
                    telemetry_ram_pct = ram_pct_raw

                # --- GPU/VRAM cache update ---
                if gpu_raw is not None:
                    telemetry_gpu = gpu_raw

                if vram_pct_raw is not None:
                    telemetry_vram = vram_pct_raw

                if vram_used_gb_raw is not None:
                    telemetry_vram_used_gb = vram_used_gb_raw

                if vram_total_gb_raw is not None:
                    telemetry_vram_total_gb = vram_total_gb_raw


            def _fmt_pct(v: float | None) -> str:
                return "N/A" if v is None else f"{v:.0f}%"

            vram_suffix = ""
            if telemetry_vram_used_gb is not None and telemetry_vram_total_gb is not None:
                vram_suffix = f" ({telemetry_vram_used_gb:.1f} / {telemetry_vram_total_gb:.1f} GB)"
            
            ram_suffix = ""
            if telemetry_ram_used_gb is not None and telemetry_ram_total_gb is not None:
                ram_pct_txt = "N/A" if telemetry_ram_pct is None else f"{telemetry_ram_pct:.0f}%"
                ram_suffix = f"{telemetry_ram_used_gb:.1f} / {telemetry_ram_total_gb:.1f} GB ({ram_pct_txt})"

            fps_now = clock.get_fps()
            frame_ms = float(clock.get_time())

            # 🧠 ЛОГИКА: сглаживаем frametime, иначе цифры слишком "дрожат"
            FRAME_MS_EMA_ALPHA = 0.12  # 🔧 МОЖНО МЕНЯТЬ: меньше = стабильнее, больше = быстрее реагирует
            if telemetry_frame_ms_smooth is None:
                telemetry_frame_ms_smooth = frame_ms
            else:
                telemetry_frame_ms_smooth = (
                    telemetry_frame_ms_smooth * (1.0 - FRAME_MS_EMA_ALPHA) + frame_ms * FRAME_MS_EMA_ALPHA
                )

            dbg = [
                f"FPS: {fps_now:.0f}",
                f"Frame time: {(telemetry_frame_ms_smooth if telemetry_frame_ms_smooth is not None else frame_ms):.1f} ms",
                f"CPU load: {_fmt_pct(telemetry_cpu_smooth)}",
                f"GPU load: {_fmt_pct(telemetry_gpu)}",
                f"VRAM used: {_fmt_pct(telemetry_vram)}{vram_suffix}",
                f"RAM used: {ram_suffix if ram_suffix else 'N/A'}",
            ]

             # ====================================================
            # ✅ Цветовые индикаторы (green/orange/red)
            # ====================================================

            # 🔧 МОЖНО МЕНЯТЬ: пороги для процентов
            OK_PCT = 50.0        # <= ok
            WARN_PCT = 80.0      # <= warn, > warn = bad

            # 🔧 МОЖНО МЕНЯТЬ: пороги для FPS относительно target fps
            OK_FPS_RATIO = 0.90   # >= 90% от target = ok
            WARN_FPS_RATIO = 0.60 # >= 60% = warn, ниже = bad

            COLOR_OK = (120, 220, 120)     # зелёный
            COLOR_WARN = (255, 170, 60)    # оранжевый
            COLOR_BAD = (235, 80, 80)      # красный
            COLOR_NA = (160, 160, 170)     # N/A
            COLOR_TEXT_DIM = COLOR_NA  # 🔧 МОЖНО МЕНЯТЬ: цвет для None/неизвестных значений

            def _grade_pct(p: float | None) -> tuple[int, int, int]:
                if p is None:
                    return COLOR_NA
                if p <= OK_PCT:
                    return COLOR_OK
                if p <= WARN_PCT:
                    return COLOR_WARN
                return COLOR_BAD

            def _grade_fps(cur_fps: float) -> tuple[int, int, int]:
                # target fps = переменная fps из параметров _run_editor_impl
                target = float(fps) if fps else 60.0
                ratio = cur_fps / target if target > 0 else 1.0
                if ratio >= OK_FPS_RATIO:
                    return COLOR_OK
                if ratio >= WARN_FPS_RATIO:
                    return COLOR_WARN
                return COLOR_BAD

            def _grade_frame_ms(ms: float | None) -> tuple[int, int, int]:
                """
                🧠 ЛОГИКА:
                16 ms  ≈ 60 FPS  → зелёный
                33 ms  ≈ 30 FPS  → оранжевый
                > 33   → красный
                """
                if ms is None:
                    return COLOR_TEXT_DIM

                if ms <= 18:
                    return COLOR_OK
                if ms <= 33:
                    return COLOR_WARN
                return COLOR_BAD

            # ------------------------------------------------
            # 🔧 НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ
            # ------------------------------------------------
            PAD_X = 10        # внутренние отступы
            PAD_Y = 6
            LINE_GAP = 4
            BG_ALPHA = 140    # 0..255 прозрачность
            BG_COLOR = (20, 20, 24)
            RADIUS = 8
            TEXT_COLOR = (230, 230, 90)

            # ------------------------------------------------
            # считаем размеры текста (с учётом индикатора)
            # ------------------------------------------------
            IND_SIZE = 10  # 🔧 МОЖНО МЕНЯТЬ: размер квадратика
            IND_GAP = 8    # 🔧 МОЖНО МЕНЯТЬ: зазор между квадратиком и текстом

            # Цвет индикатора для каждой строки
            line_colors = [
                _grade_fps(fps_now),               # FPS
                _grade_frame_ms(telemetry_frame_ms_smooth if telemetry_frame_ms_smooth is not None else frame_ms),        # Frame time
                _grade_pct(telemetry_cpu_smooth), # CPU
                _grade_pct(telemetry_gpu),        # GPU
                _grade_pct(telemetry_vram),       # VRAM
                _grade_pct(telemetry_ram_pct),    # RAM
            ]

            surfaces = [font.render(t, True, TEXT_COLOR) for t in dbg]

            max_text_w = max(s.get_width() for s in surfaces)
            max_w = IND_SIZE + IND_GAP + max_text_w
            total_h = sum(s.get_height() for s in surfaces) + LINE_GAP * (len(surfaces) - 1)

            box_w = max_w + PAD_X * 2
            box_h = total_h + PAD_Y * 2

            # ------------------------------------------------
            # позиция: под кнопкой "Выход"
            # ------------------------------------------------
            box_x = btn_exit.right - box_w
            box_y = btn_exit.bottom + 8

            # ------------------------------------------------
            # рисуем полупрозрачный фон
            # ------------------------------------------------
            overlay = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            overlay.fill((*BG_COLOR, BG_ALPHA))
            screen.blit(overlay, (box_x, box_y))

            pygame.draw.rect(
                screen,
                (80, 80, 95),
                (box_x, box_y, box_w, box_h),
                1,
                border_radius=RADIUS,
            )

            # ------------------------------------------------
            # рисуем индикатор + текст
            # ------------------------------------------------
            y = box_y + PAD_Y
            for i, surf in enumerate(surfaces):
                # индикатор
                c = line_colors[i] if i < len(line_colors) else COLOR_NA
                ind_x = box_x + PAD_X
                ind_y = y + (surf.get_height() - IND_SIZE) // 2
                pygame.draw.rect(screen, c, (ind_x, ind_y, IND_SIZE, IND_SIZE), border_radius=2)

                # текст
                text_x = ind_x + IND_SIZE + IND_GAP
                screen.blit(surf, (text_x, y))

                y += surf.get_height() + LINE_GAP



        if settings_open:
            _draw_dim_overlay_only(alpha=110)  # 🔧 МОЖНО МЕНЯТЬ: степень затемнения
            panel_rect = _settings_panel_rect()
            checkbox_rect = _settings_checkbox_fullscreen_rect(panel_rect)
            debug_rect = _settings_checkbox_debug_rect(panel_rect)

            pygame.draw.rect(screen, (32, 32, 42), panel_rect)  # 🔧 МОЖНО МЕНЯТЬ
            pygame.draw.rect(screen, BUTTON_BORDER_COLOR, panel_rect, 2)

            screen.blit(
                font.render("Настройки", True, EDITOR_TEXT_COLOR),
                (panel_rect.x + 12, panel_rect.y + 10),
            )

            pygame.draw.rect(screen, (50, 50, 70), checkbox_rect, 2)  # 🔧 МОЖНО МЕНЯТЬ

            if engine_settings.get("fullscreen", False):
                pygame.draw.line(screen, (120, 220, 120), checkbox_rect.topleft, checkbox_rect.bottomright, 3)
                pygame.draw.line(screen, (120, 220, 120), checkbox_rect.topright, checkbox_rect.bottomleft, 3)

            label = font.render("Полноэкранный режим", True, EDITOR_TEXT_COLOR)
            screen.blit(label, (checkbox_rect.right + 10, checkbox_rect.y - 2))

            # --- Debug overlay ---
            pygame.draw.rect(screen, (50, 50, 70), debug_rect, 2)  # 🔧 МОЖНО МЕНЯТЬ
            if engine_settings.get("debug_overlay", False):
                pygame.draw.line(screen, (120, 220, 120), debug_rect.topleft, debug_rect.bottomright, 3)
                pygame.draw.line(screen, (120, 220, 120), debug_rect.topright, debug_rect.bottomleft, 3)

            label2 = font.render("Отладочная информация", True, EDITOR_TEXT_COLOR)
            screen.blit(label2, (debug_rect.right + 10, debug_rect.y - 2))

        pygame.display.flip()

    pygame.quit()


def run_editor(*args, **kwargs):
    if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
        kwargs = dict(args[0])
        args = ()

    if args and len(args) >= 5:
        return _run_editor_impl(*args[:5])

    def _pick(d: dict, *names):
        for n in names:
            if n in d and d[n] is not None:
                return d[n]
        return None

    window_width = _pick(kwargs, "window_width", "width", "w", "WINDOW_WIDTH")
    window_height = _pick(kwargs, "window_height", "height", "h", "WINDOW_HEIGHT")
    window_title = _pick(kwargs, "window_title", "title", "caption", "WINDOW_TITLE")
    fps = _pick(kwargs, "fps", "FPS", "target_fps")
    projects_dir = _pick(kwargs, "projects_dir", "projects_path", "PROJECTS_DIR")
    fullscreen = _pick(kwargs, "fullscreen", "FULLSCREEN")

    try:
        from config_engine import WINDOW_WIDTH as _DW, WINDOW_HEIGHT as _DH, FPS as _DFPS
    except Exception:
        _DW, _DH, _DFPS = 1280, 720, 60  # 🔧 МОЖНО МЕНЯТЬ

    if window_width is None:
        window_width = _DW
    if window_height is None:
        window_height = _DH
    if fps is None:
        fps = _DFPS
    if fullscreen is None:
        fullscreen = False
    if window_title is None:
        window_title = "DragonEngine"
    if projects_dir is None:
        projects_dir = (Path(__file__).resolve().parents[1] / "projects")  # 🔧 МОЖНО МЕНЯТЬ

    if not isinstance(projects_dir, Path):
        projects_dir = Path(str(projects_dir))

    return _run_editor_impl(
        window_width=int(window_width),
        window_height=int(window_height),
        window_title=str(window_title),
        fps=int(fps),
        projects_dir=projects_dir,
        fullscreen=bool(fullscreen),
    )
