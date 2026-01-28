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

    # ============================================================
    # ✅ ДИСПЛЕЙ-РЕЖИМ (окно / fullscreen)
    # ============================================================
    def _apply_display_mode(fullscreen_on: bool):
        """🧠 ЛОГИКА:
        Переключаем режим окна.

        Важно:
        - чтобы tkinter окна НЕ сворачивали движок, используем borderless fullscreen (NOFRAME)
        - чтобы borderless реально растягивался при переключении из окна, делаем display.quit/init
        """
        # 🔧 МОЖНО МЕНЯТЬ: True = borderless fullscreen (НЕ сворачивается), False = pygame.FULLSCREEN (может сворачиваться)
        USE_BORDERLESS_FULLSCREEN = True  # 🔧 МОЖНО МЕНЯТЬ

        # 🔧 МОЖНО МЕНЯТЬ: включать RESIZABLE в оконном режиме (если захочешь)
        WINDOW_RESIZABLE = False  # 🔧 МОЖНО МЕНЯТЬ

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

        local_screen = pygame.display.set_mode((window_width, window_height), flags_local)
        w, h = local_screen.get_size()
        return local_screen, w, h

    screen, win_w, win_h = _apply_display_mode(bool(fullscreen))
    pygame.display.set_caption(window_title)
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
    manager_y = TITLE_Y + title_font.size(title_text)[1] + TITLE_GAP_Y

    ui_buttons_y = max(UI_TOP_Y, manager_y + font.get_height() + 10)

    # ✅ Кнопка "Выход" — ВЕРХНИЙ ПРАВЫЙ УГОЛ (меньше стандартной)
    EXIT_BTN_W = int(BUTTON_W * 0.72)  # 🔧 МОЖНО МЕНЯТЬ
    EXIT_BTN_H = int(BUTTON_H * 0.78)  # 🔧 МОЖНО МЕНЯТЬ
    EXIT_BTN_MARGIN = 10  # 🔧 МОЖНО МЕНЯТЬ

    EXIT_BTN_X = win_w - EXIT_BTN_W - EXIT_BTN_MARGIN
    EXIT_BTN_Y = EXIT_BTN_MARGIN
    btn_exit = pygame.Rect(EXIT_BTN_X, EXIT_BTN_Y, EXIT_BTN_W, EXIT_BTN_H)

    # ✅ Настройки движка (persisted)
    engine_settings = load_settings()
    engine_settings["fullscreen"] = bool(fullscreen)
    settings_open = False

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
    SETTINGS_BTN_X = UI_MARGIN_X
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
    PROJECT_LIST_Y = 240  # 🔧 МОЖНО МЕНЯТЬ
    PROJECT_ITEM_W = 420  # 🔧 МОЖНО МЕНЯТЬ
    PROJECT_ITEM_H = 36  # 🔧 МОЖНО МЕНЯТЬ
    PROJECT_ITEM_GAP = 8  # 🔧 МОЖНО МЕНЯТЬ

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

    BOTTOM_SAFE_PAD = 18  # 🔧 МОЖНО МЕНЯТЬ
    STATUS_GAP = 10  # 🔧 МОЖНО МЕНЯТЬ

    def _selected_buttons_panel_x() -> int:
        return UI_MARGIN_X + PROJECT_ITEM_W + UI_GAP_X

    def _selected_button_width() -> int:
        panel_x = _selected_buttons_panel_x()
        available = win_w - panel_x - UI_MARGIN_X
        w = int((available - SELECTED_BUTTON_GAP_X) / 2)
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

        result = run_scene_editor(scene_path, win_w, win_h, fps)

        if result == "quit":
            force_quit(0)

        pygame.display.set_caption(window_title)
        screen, win_w, win_h = _apply_display_mode(bool(engine_settings.get("fullscreen", False)))
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
        PANEL_H = 96   # 🔧 МОЖНО МЕНЯТЬ
        PANEL_MARGIN_Y = 6  # 🔧 МОЖНО МЕНЯТЬ

        panel_x = btn_settings.x
        panel_y = btn_settings.bottom + PANEL_MARGIN_Y
        return pygame.Rect(panel_x, panel_y, PANEL_W, PANEL_H)

    def _settings_checkbox_fullscreen_rect(panel_rect: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(panel_rect.x + 12, panel_rect.y + 44, 20, 20)

    running = True
    while running:
        clock.tick(fps)
        mouse_pos = pygame.mouse.get_pos()

        win_w, win_h = screen.get_size()
        _update_exit_button()

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

                    if checkbox_rect.collidepoint(pos):
                        engine_settings["fullscreen"] = not bool(engine_settings.get("fullscreen", False))
                        save_settings(engine_settings)

                        fullscreen = bool(engine_settings["fullscreen"])

                        screen, win_w, win_h = _apply_display_mode(fullscreen)
                        _update_exit_button()

                        pygame.display.set_caption(window_title)
                        pygame.event.clear()

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

        screen.blit(font.render("Менеджер проектов:", True, EDITOR_TEXT_COLOR), (UI_MARGIN_X, manager_y))

        _draw_button(screen, font, btn_create, "Создать проект", mouse_pos)
        _draw_button(screen, font, btn_last_project, "Последний проект", mouse_pos)
        _draw_button(screen, font, btn_open_project, "Открыть проект", mouse_pos)

        screen.blit(font.render("Проекты:", True, EDITOR_TEXT_COLOR), (UI_MARGIN_X, PROJECT_LIST_Y - 30))

        y = PROJECT_LIST_Y
        if all_projects:
            for i, p in enumerate(all_projects):
                item_rect = pygame.Rect(PROJECT_LIST_X, y, PROJECT_ITEM_W, PROJECT_ITEM_H)

                if selected_project_index == i:
                    pygame.draw.rect(screen, (70, 100, 160), item_rect)  # 🔧 МОЖНО МЕНЯТЬ
                else:
                    pygame.draw.rect(screen, (40, 40, 46), item_rect)  # 🔧 МОЖНО МЕНЯТЬ

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

        if settings_open:
            _draw_dim_overlay_only(alpha=110)  # 🔧 МОЖНО МЕНЯТЬ: степень затемнения
            panel_rect = _settings_panel_rect()
            checkbox_rect = _settings_checkbox_fullscreen_rect(panel_rect)

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
