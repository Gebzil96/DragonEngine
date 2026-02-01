import os  # ✅ фиксация позиции окна SDL
import sys  # ✅ win32 check
import ctypes  # ✅ WinAPI: стиль окна
from ctypes import wintypes  # ✅ типы WinAPI
import json  # 🧠 ЛОГИКА: загрузка/сохранение сцены
from pathlib import Path  # 🧠 ЛОГИКА: пути

# ============================================================
# ✅ DEBUG TELEMETRY (как в менеджере проектов / editor_app.py)
# ============================================================
try:
    import psutil  # CPU/RAM
    _PSUTIL_OK = True
except Exception:
    psutil = None
    _PSUTIL_OK = False

try:
    import pynvml  # GPU/VRAM (NVIDIA)
    _NVML_OK = True
except Exception:
    pynvml = None
    _NVML_OK = False

TELEMETRY_UPDATE_MS = 500  # 🔧 МОЖНО МЕНЯТЬ: частота обновления телеметрии
CPU_SMOOTH_ALPHA = 0.22    # 🔧 МОЖНО МЕНЯТЬ: сглаживание CPU (EMA)


def _get_cpu_percent() -> float | None:
    """🧠 ЛОГИКА: CPU % (может вернуть None если psutil отсутствует/отвалился)"""
    if not _PSUTIL_OK:
        return None
    try:
        return float(psutil.cpu_percent(interval=None))
    except Exception:
        return None


def _get_ram_metrics() -> tuple[float | None, float | None, float | None]:
    """
    🧠 ЛОГИКА: RAM -> (percent, used_gb, total_gb)
    """
    if not _PSUTIL_OK:
        return None, None, None
    try:
        vm = psutil.virtual_memory()
        used_gb = vm.used / (1024 ** 3)
        total_gb = vm.total / (1024 ** 3)
        return float(vm.percent), float(used_gb), float(total_gb)
    except Exception:
        return None, None, None


_NVML_INITIALIZED = False


def _nvml_init_once() -> bool:
    """🧠 ЛОГИКА: NVML init один раз, чтобы не лагало и не падало."""
    global _NVML_INITIALIZED
    if not _NVML_OK:
        return False
    if _NVML_INITIALIZED:
        return True
    try:
        pynvml.nvmlInit()
        _NVML_INITIALIZED = True
        return True
    except Exception:
        return False


def _get_nvidia_gpu_metrics() -> tuple[float | None, float | None, float | None, float | None]:
    """
    🧠 ЛОГИКА: GPU util% и VRAM (percent, used_gb, total_gb).
    Возвращает: (gpu_util, vram_percent, vram_used_gb, vram_total_gb)
    """
    if not _nvml_init_once():
        return None, None, None, None

    try:
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)

        gpu_util = float(util.gpu)
        used_gb = float(mem.used) / (1024 ** 3)
        total_gb = float(mem.total) / (1024 ** 3)
        vram_percent = float((mem.used / mem.total) * 100.0) if mem.total else None

        return gpu_util, vram_percent, used_gb, total_gb
    except Exception:
        return None, None, None, None


def _perf_color(pct: float | None) -> tuple[int, int, int]:
    """
    🧠 ЛОГИКА: цвет-индикатор как ты просил ранее:
    зеленый = идеально, оранжевый = терпимо, красный = плохо
    """
    if pct is None:
        return (180, 180, 190)  # N/A
    if pct < 60:
        return (120, 220, 120)  # green
    if pct < 85:
        return (240, 170, 70)   # orange
    return (230, 90, 90)        # red


def _fmt_gb(x: float | None) -> str:
    if x is None:
        return "N/A"
    return f"{x:.1f}GB"


import pygame  # 🧠 ЛОГИКА: рендер/события

# ============================================================
# ✅ Импорты конфига (поддерживаем оба варианта: engine.config_engine и config_engine)
# ============================================================
try:
    # вариант, когда config_engine лежит в пакете engine
    from engine.config_engine import (  # type: ignore
        EDITOR_BG_COLOR,
        EDITOR_TEXT_COLOR,
        DEFAULT_FONT_SIZE,
        BUTTON_BG_COLOR,
        BUTTON_HOVER_COLOR,
        BUTTON_BORDER_COLOR,
        BUTTON_BORDER_WIDTH,
        BUTTON_TEXT_COLOR,
        BUTTON_W,
        BUTTON_H,
        EDGE_PAD,
        UI_GAP_X,
    )
except Exception:
    # вариант, как в editor_app.py (from config_engine import ...)
    from config_engine import (  # type: ignore
        EDITOR_BG_COLOR,
        EDITOR_TEXT_COLOR,
        DEFAULT_FONT_SIZE,
        BUTTON_BG_COLOR,
        BUTTON_HOVER_COLOR,
        BUTTON_BORDER_COLOR,
        BUTTON_BORDER_WIDTH,
        BUTTON_TEXT_COLOR,
        BUTTON_W,
        BUTTON_H,
        EDGE_PAD,
        UI_GAP_X,
    )

from engine_settings import load_settings, save_settings  # ✅ настройки движка

# ============================================================
# ✅ WinAPI: получение HWND + смена стиля окна (рамка/безрамки)
# ============================================================
def _win_get_hwnd() -> int | None:
    """🧠 ЛОГИКА: получить HWND окна pygame (Windows only)."""
    if sys.platform != "win32":
        return None
    try:
        info = pygame.display.get_wm_info()
        hwnd = info.get("window")
        return int(hwnd) if hwnd else None
    except Exception:
        return None


def _win_set_borderless(hwnd: int, borderless: bool) -> None:
    """
    🧠 ЛОГИКА:
    Жёстко переключаем стиль окна:
    - borderless=True  -> WS_POPUP (без рамки)
    - borderless=False -> WS_OVERLAPPEDWINDOW (нормальная рамка + заголовок + ресайз)
    """
    if sys.platform != "win32":
        return

    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)

        GWL_STYLE = -16

        WS_OVERLAPPED = 0x00000000
        WS_POPUP = 0x80000000
        WS_CAPTION = 0x00C00000
        WS_SYSMENU = 0x00080000
        WS_THICKFRAME = 0x00040000
        WS_MINIMIZEBOX = 0x00020000
        WS_MAXIMIZEBOX = 0x00010000

        WS_OVERLAPPEDWINDOW = (
            WS_OVERLAPPED
            | WS_CAPTION
            | WS_SYSMENU
            | WS_THICKFRAME
            | WS_MINIMIZEBOX
            | WS_MAXIMIZEBOX
        )

        if hasattr(user32, "GetWindowLongPtrW"):
            GetStyle = user32.GetWindowLongPtrW
            SetStyle = user32.SetWindowLongPtrW
        else:
            GetStyle = user32.GetWindowLongW
            SetStyle = user32.SetWindowLongW

        GetStyle.argtypes = [wintypes.HWND, ctypes.c_int]
        GetStyle.restype = ctypes.c_longlong

        SetStyle.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_longlong]
        SetStyle.restype = ctypes.c_longlong

        current = int(GetStyle(wintypes.HWND(hwnd), GWL_STYLE))

        if borderless:
            new_style = (current & ~WS_OVERLAPPEDWINDOW) | WS_POPUP
        else:
            new_style = (current & ~WS_POPUP) | WS_OVERLAPPEDWINDOW

        SetStyle(wintypes.HWND(hwnd), GWL_STYLE, new_style)

        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
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
            wintypes.HWND(hwnd),
            None,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )
    except Exception:
        pass


def _win_force_window_rect(x: int, y: int, w: int, h: int) -> None:
    """🧠 ЛОГИКА: прибиваем окно к (x,y,w,h) на Windows (иногда SDL чудит)."""
    if sys.platform != "win32":
        return

    hwnd = _win_get_hwnd()
    if not hwnd:
        return

    try:
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
            wintypes.HWND(hwnd),
            None,
            int(x),
            int(y),
            int(w),
            int(h),
            SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )
    except Exception:
        pass


# ============================================================
# ✅ APPLY DISPLAY MODE (как в менеджере проектов + жёсткий фикс рамки)
# ============================================================
def _apply_display_mode(
    windowed_size: tuple[int, int],
    fullscreen_on: bool,
) -> tuple[pygame.Surface, int, int]:
    """
    🧠 ЛОГИКА:
    fullscreen = borderless (NOFRAME) чтобы модалки/меню не сворачивали движок,
    windowed   = нормальная рамка + RESIZABLE.
    """
    USE_BORDERLESS_FULLSCREEN = True  # 🔧 МОЖНО МЕНЯТЬ: True=NOFRAME, False=FULLSCREEN
    WINDOW_RESIZABLE = True           # 🔧 МОЖНО МЕНЯТЬ

    if fullscreen_on:
        os.environ["SDL_VIDEO_CENTERED"] = "0"
        os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"

        try:
            pygame.display.quit()
        except Exception:
            pass
        pygame.display.init()

        info = pygame.display.Info()
        screen_w, screen_h = info.current_w, info.current_h

        if USE_BORDERLESS_FULLSCREEN:
            screen = pygame.display.set_mode((screen_w, screen_h), pygame.NOFRAME)
        else:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

        hwnd = _win_get_hwnd()
        if hwnd and USE_BORDERLESS_FULLSCREEN:
            _win_set_borderless(hwnd, True)
        _win_force_window_rect(0, 0, screen_w, screen_h)

        w, h = screen.get_size()
        return screen, w, h

    # ---- оконный режим ----
    try:
        pygame.display.quit()
    except Exception:
        pass
    pygame.display.init()

    flags = 0
    if WINDOW_RESIZABLE:
        flags |= pygame.RESIZABLE

    w0, h0 = windowed_size
    screen = pygame.display.set_mode((int(w0), int(h0)), flags)

    hwnd = _win_get_hwnd()
    if hwnd:
        _win_set_borderless(hwnd, False)

    w, h = screen.get_size()
    return screen, w, h


# ============================================================
# ✅ Сцена: загрузка/сохранение
# ============================================================
def load_scene(scene_path: Path):
    """🧠 ЛОГИКА: загрузка сцены из файла JSON."""
    if scene_path.exists():
        with open(scene_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return {"name": "main", "entities": []}


def save_scene(scene_path: Path, scene_data):
    """🧠 ЛОГИКА: сохраняет изменённую сцену в файл."""
    with open(scene_path, "w", encoding="utf-8") as file:
        json.dump(scene_data, file, ensure_ascii=False, indent=2)


def _get_project_name_from_scene_path(scene_path: Path) -> str:
    """🧠 ЛОГИКА: достаём имя проекта из project.json, fallback на имя папки."""
    try:
        project_root = scene_path.resolve().parent.parent
        pj = project_root / "project.json"
        if pj.exists():
            with open(pj, "r", encoding="utf-8") as f:
                data = json.load(f)
            name = data.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        return project_root.name
    except Exception:
        return "Проект"


def draw_entities(screen, entities, font):
    """🧠 ЛОГИКА: рисует все сущности на экране."""
    for entity in entities:
        if entity.get("type") == "rect":
            pygame.draw.rect(
                screen,
                (255, 255, 255),  # 🔧 МОЖНО МЕНЯТЬ
                (entity["x"], entity["y"], entity["w"], entity["h"]),
            )
            label = font.render(str(entity.get("id", "")), True, EDITOR_TEXT_COLOR)
            screen.blit(label, (entity["x"], entity["y"] - 20))  # 🔧 МОЖНО МЕНЯТЬ


def handle_entity_move(mouse_pos, selected_entity):
    """🧠 ЛОГИКА: если выбрана сущность, она двигается за мышью."""
    if selected_entity:
        selected_entity["x"], selected_entity["y"] = mouse_pos


def _draw_project_badge(screen, font, project_name: str) -> None:
    """🧠 ЛОГИКА: бейдж проекта слева сверху."""
    x = 10  # 🔧 МОЖНО МЕНЯТЬ
    y = 10  # 🔧 МОЖНО МЕНЯТЬ
    surf = font.render(f"Проект: {project_name}", True, EDITOR_TEXT_COLOR)
    screen.blit(surf, (x, y))


def _draw_button(screen, font, rect, text, mouse_pos):
    """🧠 ЛОГИКА: кнопка в стиле менеджера проектов."""
    is_hover = rect.collidepoint(mouse_pos)
    bg = BUTTON_HOVER_COLOR if is_hover else BUTTON_BG_COLOR
    pygame.draw.rect(screen, bg, rect)
    pygame.draw.rect(screen, BUTTON_BORDER_COLOR, rect, BUTTON_BORDER_WIDTH)
    label = font.render(text, True, BUTTON_TEXT_COLOR)
    screen.blit(label, label.get_rect(center=rect.center))
    return is_hover


def _draw_exit_button(screen, font, rect, text, mouse_pos):
    """🧠 ЛОГИКА: кнопка 'Выход' (краснее при hover)."""
    is_hover = rect.collidepoint(mouse_pos)
    EXIT_BG = BUTTON_BG_COLOR                 # 🔧 МОЖНО МЕНЯТЬ
    EXIT_HOVER_BG_2 = (180, 55, 55)           # 🔧 МОЖНО МЕНЯТЬ
    bg = EXIT_HOVER_BG_2 if is_hover else EXIT_BG
    pygame.draw.rect(screen, bg, rect)
    pygame.draw.rect(screen, BUTTON_BORDER_COLOR, rect, BUTTON_BORDER_WIDTH)
    label = font.render(text, True, BUTTON_TEXT_COLOR)
    screen.blit(label, label.get_rect(center=rect.center))
    return is_hover


# ============================================================
# ✅ Панели (карточка) — 1:1 как в менеджере проектов (editor_app.py)
# ============================================================
PANEL_BG_COLOR = (28, 30, 40)        # 🔧 МОЖНО МЕНЯТЬ: фон панели
PANEL_BG_ALPHA = 235                 # 🔧 МОЖНО МЕНЯТЬ: плотность (0..255)
PANEL_BORDER_COLOR = (170, 180, 220) # 🔧 МОЖНО МЕНЯТЬ: цвет рамки
PANEL_BORDER_W = 1                   # 🔧 МОЖНО МЕНЯТЬ: толщина рамки
PANEL_RADIUS = 10                    # 🔧 МОЖНО МЕНЯТЬ: скругление


def _draw_panel(screen: pygame.Surface, rect: pygame.Rect) -> None:
    """🧠 ЛОГИКА: карточка панели 1:1 как в менеджере проектов."""
    overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    overlay.fill((*PANEL_BG_COLOR, int(PANEL_BG_ALPHA)))
    screen.blit(overlay, (rect.x, rect.y))

    pygame.draw.rect(
        screen,
        PANEL_BORDER_COLOR,
        rect,
        PANEL_BORDER_W,
        border_radius=PANEL_RADIUS,
    )


# ✅ совместимость: если где-то осталось старое имя
_draw_panel_like_manager = _draw_panel


# ============================================================
# ✅ Главный цикл
# ============================================================
def run_scene_editor(scene_path, window_width, window_height, fps):
    """
    Возвраты:
    - "quit" — закрыть весь движок
    - "back" — вернуться в менеджер проектов
    """
    os.environ["SDL_VIDEO_CENTERED"] = "0"
    os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"

    engine_settings = load_settings()
    engine_settings.setdefault("fullscreen", False)
    engine_settings.setdefault("debug_overlay", False)

    last_windowed_size = (int(window_width), int(window_height))  # 🔧 МОЖНО МЕНЯТЬ

    screen, window_width, window_height = _apply_display_mode(
        windowed_size=last_windowed_size,
        fullscreen_on=bool(engine_settings.get("fullscreen", False)),
    )

    pygame.display.set_caption("Редактор сцены")

    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, DEFAULT_FONT_SIZE)

    scene_path = Path(scene_path)
    scene_data = load_scene(scene_path)
    selected_entity = None
    project_name = _get_project_name_from_scene_path(scene_path)

    # ✅ состояние меню настроек
    settings_open = False

    # ✅ кеш телеметрии (как в менеджере)
    telemetry_last_ms = 0
    telemetry_cpu_smooth = None
    telemetry_gpu = None
    telemetry_vram = None
    telemetry_vram_used_gb = None
    telemetry_vram_total_gb = None

    running = True
    while running:
        clock.tick(fps)
        mouse_pos = pygame.mouse.get_pos()

        window_width, window_height = screen.get_size()
        if not engine_settings.get("fullscreen", False):
            last_windowed_size = (int(window_width), int(window_height))

        # ---------------- UI rects ----------------
        TOP_BTN_W = int(BUTTON_W * 0.72)  # 🔧 МОЖНО МЕНЯТЬ
        TOP_BTN_H = int(BUTTON_H * 0.78)  # 🔧 МОЖНО МЕНЯТЬ
        TOP_MARGIN = EDGE_PAD            # 🔧 МОЖНО МЕНЯТЬ

        settings_rect = pygame.Rect(TOP_MARGIN, TOP_MARGIN, TOP_BTN_W, TOP_BTN_H)
        exit_rect = pygame.Rect(window_width - TOP_BTN_W - TOP_MARGIN, TOP_MARGIN, TOP_BTN_W, TOP_BTN_H)
        back_rect = pygame.Rect(exit_rect.x - TOP_BTN_W - UI_GAP_X, TOP_MARGIN, TOP_BTN_W, TOP_BTN_H)

        # ---------------- Settings panel layout ----------------
        panel_rect = None
        cb_full = None
        cb_dbg = None

        # Эти константы ты просил держать 1:1 как в менеджере:
        TITLE_Y = 10     # 🔧 НЕ МЕНЯТЬ
        ROW1_Y = 44      # 🔧 НЕ МЕНЯТЬ
        ROW2_Y = 80      # 🔧 НЕ МЕНЯТЬ

        if settings_open:
            PANEL_GAP_Y = 6   # 🔧 МОЖНО МЕНЯТЬ
            PANEL_W = 320     # 🔧 МОЖНО МЕНЯТЬ
            PANEL_H = 120     # 🔧 МОЖНО МЕНЯТЬ

            panel_rect = pygame.Rect(settings_rect.x, settings_rect.bottom + PANEL_GAP_Y, PANEL_W, PANEL_H)

            row1_y = panel_rect.y + ROW1_Y
            row2_y = panel_rect.y + ROW2_Y
            cb_size = 20
            cb_x = panel_rect.x + 12
            cb_full = pygame.Rect(cb_x, row1_y, cb_size, cb_size)
            cb_dbg = pygame.Rect(cb_x, row2_y, cb_size, cb_size)

        # ---------------- Events ----------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # верхние кнопки
                if exit_rect.collidepoint(event.pos):
                    return "quit"

                if back_rect.collidepoint(event.pos) and not settings_open:
                    return "back"

                if settings_rect.collidepoint(event.pos):
                    settings_open = not settings_open
                    continue

                # ✅ меню открыто: съедаем клики и обрабатываем чекбоксы
                if settings_open and panel_rect is not None:
                    # клик вне панели — закрываем (как в менеджере)
                    if not panel_rect.collidepoint(event.pos):
                        settings_open = False
                        continue

                    # клик по чекбоксам
                    if cb_full is not None and cb_full.collidepoint(event.pos):
                        engine_settings["fullscreen"] = not engine_settings.get("fullscreen", False)
                        save_settings(engine_settings)

                        screen, window_width, window_height = _apply_display_mode(
                            windowed_size=last_windowed_size,
                            fullscreen_on=bool(engine_settings.get("fullscreen", False)),
                        )
                        continue

                    if cb_dbg is not None and cb_dbg.collidepoint(event.pos):
                        engine_settings["debug_overlay"] = not engine_settings.get("debug_overlay", False)
                        save_settings(engine_settings)
                        continue

                    # клик внутри панели, но не по пунктам
                    continue

                # выбор сущности (только когда меню закрыто)
                for entity in scene_data.get("entities", []):
                    if entity.get("type") != "rect":
                        continue
                    r = pygame.Rect(entity["x"], entity["y"], entity["w"], entity["h"])
                    if r.collidepoint(mouse_pos):
                        selected_entity = entity

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                selected_entity = None

        # ---------------- Render ----------------
        screen.fill(EDITOR_BG_COLOR)

        # ✅ DIM BACKGROUND (как в Менеджере проектов)
        if settings_open:
            DIM_ALPHA = 120  # 🔧 МОЖНО МЕНЯТЬ
            dim = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
            dim.fill((0, 0, 0, DIM_ALPHA))
            screen.blit(dim, (0, 0))

        _draw_project_badge(screen, font, project_name)

        _draw_button(screen, font, settings_rect, "Настройки", mouse_pos)
        _draw_button(screen, font, back_rect, "К проектам", mouse_pos)
        _draw_exit_button(screen, font, exit_rect, "Выход", mouse_pos)

        draw_entities(screen, scene_data.get("entities", []), font)

        if selected_entity:
            handle_entity_move(mouse_pos, selected_entity)

        # settings panel render
        if settings_open and panel_rect is not None and cb_full is not None and cb_dbg is not None:
            _draw_panel_like_manager(screen, panel_rect)

            title = font.render("Настройки", True, EDITOR_TEXT_COLOR)
            screen.blit(title, (panel_rect.x + 12, panel_rect.y + TITLE_Y))

            pygame.draw.rect(screen, (80, 80, 90), cb_full, 2)
            if engine_settings.get("fullscreen", False):
                pygame.draw.line(screen, (120, 220, 120), cb_full.topleft, cb_full.bottomright, 3)
                pygame.draw.line(screen, (120, 220, 120), cb_full.topright, cb_full.bottomleft, 3)
            screen.blit(
                font.render("Полноэкранный режим", True, EDITOR_TEXT_COLOR),
                (panel_rect.x + 44, cb_full.y - 1),
            )

            pygame.draw.rect(screen, (80, 80, 90), cb_dbg, 2)
            if engine_settings.get("debug_overlay", False):
                pygame.draw.line(screen, (120, 220, 120), cb_dbg.topleft, cb_dbg.bottomright, 3)
                pygame.draw.line(screen, (120, 220, 120), cb_dbg.topright, cb_dbg.bottomleft, 3)
            screen.blit(
                font.render("Отладочная информация", True, EDITOR_TEXT_COLOR),
                (panel_rect.x + 44, cb_dbg.y - 1),
            )

        # ====================================================
        # ✅ Debug overlay — 1:1 как в Менеджере проектов (editor_app.py)
        # ====================================================
        if engine_settings.get("debug_overlay", False):
            now_ms = pygame.time.get_ticks()

            # ✅ обновляем телеметрию не каждый кадр (как в менеджере)
            need_refresh = (now_ms - telemetry_last_ms) >= TELEMETRY_UPDATE_MS
            if telemetry_cpu_smooth is None or telemetry_gpu is None or telemetry_vram is None:
                need_refresh = True

            if need_refresh:
                telemetry_last_ms = now_ms

                # CPU raw -> EMA smoothing
                cpu_raw = _get_cpu_percent()
                if cpu_raw is not None:
                    if telemetry_cpu_smooth is None:
                        telemetry_cpu_smooth = float(cpu_raw)
                    else:
                        telemetry_cpu_smooth = (
                            telemetry_cpu_smooth * (1.0 - CPU_SMOOTH_ALPHA)
                            + float(cpu_raw) * CPU_SMOOTH_ALPHA
                        )

                gpu_raw, vram_pct_raw, vram_used_gb_raw, vram_total_gb_raw = _get_nvidia_gpu_metrics()

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

            fps_now = clock.get_fps()

            dbg = [
                f"FPS: {fps_now:.0f}",
                f"CPU load: {_fmt_pct(telemetry_cpu_smooth)}",
                f"GPU load: {_fmt_pct(telemetry_gpu)}",
                f"VRAM used: {_fmt_pct(telemetry_vram)}{vram_suffix}",
            ]

            # ====================================================
            # ✅ Цветовые индикаторы (green/orange/red) — 1:1
            # ====================================================
            OK_PCT = 50.0        # <= ok
            WARN_PCT = 80.0      # <= warn, > warn = bad

            OK_FPS_RATIO = 0.90   # >= 90% от target = ok
            WARN_FPS_RATIO = 0.60 # >= 60% = warn, ниже = bad

            COLOR_OK = (120, 220, 120)
            COLOR_WARN = (255, 170, 60)
            COLOR_BAD = (235, 80, 80)
            COLOR_NA = (160, 160, 170)

            def _grade_pct(p: float | None) -> tuple[int, int, int]:
                if p is None:
                    return COLOR_NA
                if p <= OK_PCT:
                    return COLOR_OK
                if p <= WARN_PCT:
                    return COLOR_WARN
                return COLOR_BAD

            def _grade_fps(cur_fps: float) -> tuple[int, int, int]:
                target = float(fps) if fps else 60.0
                ratio = cur_fps / target if target > 0 else 1.0
                if ratio >= OK_FPS_RATIO:
                    return COLOR_OK
                if ratio >= WARN_FPS_RATIO:
                    return COLOR_WARN
                return COLOR_BAD

            # ------------------------------------------------
            # 🔧 НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ — 1:1 как в менеджере
            # ------------------------------------------------
            PAD_X = 10
            PAD_Y = 6
            LINE_GAP = 4
            BG_ALPHA = 140
            BG_COLOR = (20, 20, 24)
            RADIUS = 8
            TEXT_COLOR = (230, 230, 90)

            IND_SIZE = 10  # 🔧 МОЖНО МЕНЯТЬ
            IND_GAP = 8    # 🔧 МОЖНО МЕНЯТЬ

            line_colors: list[tuple[int, int, int]] = [
                _grade_fps(fps_now),              # FPS
                _grade_pct(telemetry_cpu_smooth), # CPU
                _grade_pct(telemetry_gpu),        # GPU
                _grade_pct(telemetry_vram),       # VRAM
            ]

            surfaces = [font.render(t, True, TEXT_COLOR) for t in dbg]

            max_text_w = max(s.get_width() for s in surfaces)
            max_w = IND_SIZE + IND_GAP + max_text_w
            total_h = sum(s.get_height() for s in surfaces) + LINE_GAP * (len(surfaces) - 1)

            box_w = max_w + PAD_X * 2
            box_h = total_h + PAD_Y * 2

            # ------------------------------------------------
            # позиция: под кнопкой "Выход" — 1:1
            # ------------------------------------------------
            box_x = exit_rect.right - box_w
            box_y = exit_rect.bottom + 8

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

            y = box_y + PAD_Y
            for i, surf in enumerate(surfaces):
                c = line_colors[i] if i < len(line_colors) else COLOR_NA
                ind_x = box_x + PAD_X
                ind_y = y + (surf.get_height() - IND_SIZE) // 2
                pygame.draw.rect(screen, c, (ind_x, ind_y, IND_SIZE, IND_SIZE), border_radius=2)

                text_x = ind_x + IND_SIZE + IND_GAP
                screen.blit(surf, (text_x, y))

                y += surf.get_height() + LINE_GAP


        pygame.display.flip()

        # 🔧 МОЖНО МЕНЯТЬ: горячая клавиша сохранения сцены
        if pygame.key.get_pressed()[pygame.K_s]:
            save_scene(scene_path, scene_data)

    return "back"
