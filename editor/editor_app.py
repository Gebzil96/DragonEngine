import sys
import pygame
import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox  # ✅ НОВОЕ: подтверждение удаления
from pathlib import Path
import json
import math  # ✅ НОВОЕ: для плавной анимации (sin)

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
    list_all_projects,     # ✅ ВСЕ проекты из реестра
    register_project,      # ✅ регистрируем любой созданный/открытый проект
    open_last_project,
    save_last_project,
    open_project_by_path,
    delete_project,        # ✅ УДАЛЕНИЕ проекта
)

from editor.scene_editor import run_scene_editor  # 🧠 ЛОГИКА: редактор сцены


# 🧠 ЛОГИКА: tkinter нужен только для диалогов
root = tk.Tk()
root.withdraw()


class Project:
    """🧠 ЛОГИКА: локальный класс проекта (используется при создании)."""

    def __init__(self, path: Path, name: str):
        self.root = path                      # 🧠 ЛОГИКА: корневая папка проекта
        self.name = name                      # 🧠 ЛОГИКА: имя проекта
        self.start_scene: Path | None = None  # 🧠 ЛОГИКА: путь к стартовой сцене

    def set_start_scene(self, scene_path: Path):
        self.start_scene = scene_path


def _draw_lines(screen, font, lines, x, y, color):
    """🧠 ЛОГИКА: рисует список строк текста."""
    yy = y  # 🔧 МОЖНО МЕНЯТЬ: стартовый Y
    for line in lines:
        surf = font.render(line, True, color)  # 🧠 ЛОГИКА: рендер текста
        screen.blit(surf, (x, yy))             # 🧠 ЛОГИКА: вывод на экран
        yy += surf.get_height() + 6            # 🔧 МОЖНО МЕНЯТЬ: расстояние между строками


def _draw_button(screen, font, rect, text, mouse_pos):
    """🧠 ЛОГИКА: рисует кнопку (hover-эффект через цвета из config)."""
    is_hover = rect.collidepoint(mouse_pos)  # 🧠 ЛОГИКА: наведение
    bg = BUTTON_HOVER_COLOR if is_hover else BUTTON_BG_COLOR  # 🧠 ЛОГИКА: фон кнопки

    pygame.draw.rect(screen, bg, rect)  # 🧠 ЛОГИКА: фон
    pygame.draw.rect(screen, BUTTON_BORDER_COLOR, rect, BUTTON_BORDER_WIDTH)  # 🧠 ЛОГИКА: рамка

    label = font.render(text, True, BUTTON_TEXT_COLOR)  # 🧠 ЛОГИКА: текст
    screen.blit(label, label.get_rect(center=rect.center))  # 🧠 ЛОГИКА: центрируем текст
    return is_hover


def _clamp_int(v: float, lo: int, hi: int) -> int:
    """🧠 ЛОГИКА: безопасно ограничиваем значение и приводим к int."""
    return int(max(lo, min(hi, v)))


def _blend_color(base_rgb: tuple[int, int, int], add_rgb: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """
    🧠 ЛОГИКА: смешиваем цвета.
    t=0 -> base, t=1 -> base+add (с ограничением).
    """
    r = _clamp_int(base_rgb[0] + add_rgb[0] * t, 0, 255)
    g = _clamp_int(base_rgb[1] + add_rgb[1] * t, 0, 255)
    b = _clamp_int(base_rgb[2] + add_rgb[2] * t, 0, 255)
    return (r, g, b)


def check_scene_file(scene_path: Path) -> bool:
    """🧠 ЛОГИКА: проверка существования сцены."""
    print(f"Проверяем наличие сцены по пути: {scene_path}")
    if scene_path.exists():
        print(f"Сцена найдена: {scene_path}")
        return True
    print(f"Ошибка: Сцена не найдена по пути: {scene_path}")
    return False


def create_scene_file(scene_path: Path):
    """🧠 ЛОГИКА: создаёт дефолтную сцену."""
    scene_data = {
        "name": "MainScene",
        "entities": []  # 🔧 МОЖНО МЕНЯТЬ: стартовые сущности
    }
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    with open(scene_path, "w", encoding="utf-8") as scene_file:
        json.dump(scene_data, scene_file, ensure_ascii=False, indent=2)
    print(f"Сцена была успешно создана: {scene_path}")


def create_project(project_dir: Path, project_name: str) -> Project | None:
    """🧠 ЛОГИКА: создаёт проект в выбранной папке."""
    if not project_dir.exists():
        project_dir.mkdir(parents=True)

    project_path = project_dir / project_name
    if project_path.exists():
        print(f"Ошибка: Проект с именем '{project_name}' уже существует.")
        return None

    project_path.mkdir(parents=True)

    # 🧠 ЛОГИКА: структура проекта
    (project_path / "scenes").mkdir(parents=True, exist_ok=True)
    (project_path / "assets").mkdir(parents=True, exist_ok=True)
    (project_path / "scripts").mkdir(parents=True, exist_ok=True)

    # 🧠 ЛОГИКА: project.json
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

    # 🧠 ЛОГИКА: создаём сцену при необходимости
    if project.start_scene and not project.start_scene.exists():
        create_scene_file(project.start_scene)

    # ✅ РЕЕСТР: добавляем в общий список и запоминаем как последний
    register_project(project.root)
    save_last_project(project.root)

    return project


def open_selected_project() -> Path | None:
    """🧠 ЛОГИКА: выбираем папку проекта через диалог."""
    folder = filedialog.askdirectory(title="Выберите папку с проектом")
    if not folder:
        return None
    return Path(folder)


# ============================================================
# ✅ ВНУТРЕННЯЯ РЕАЛИЗАЦИЯ (UI НЕ МЕНЯЕМ)
# ============================================================
def _run_editor_impl(window_width: int, window_height: int, window_title: str, fps: int, projects_dir: Path):
    """🧠 ЛОГИКА: менеджер проектов."""
    pygame.init()
    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption(window_title)
    clock = pygame.time.Clock()

    font = pygame.font.SysFont(None, DEFAULT_FONT_SIZE)
    title_font = pygame.font.SysFont(None, TITLE_FONT_SIZE)

    status_message = ""

    # ------------------------------------------------------------
    # ✅ ВАЖНО: считаем Y для строки "Менеджер проектов:" заранее
    # и ставим кнопки НИЖЕ неё, чтобы они не закрашивали текст.
    # ------------------------------------------------------------
    title_text = "DragonEngine"
    manager_y = TITLE_Y + title_font.size(title_text)[1] + TITLE_GAP_Y

    ui_buttons_y = max(
        UI_TOP_Y,                           # 🔧 МОЖНО МЕНЯТЬ: базовый Y кнопок из config
        manager_y + font.get_height() + 10  # 🔧 МОЖНО МЕНЯТЬ: отступ после строки
    )

    # --- КНОПКИ ---
    btn_create = pygame.Rect(UI_MARGIN_X, ui_buttons_y, BUTTON_W, BUTTON_H)
    btn_last_project = pygame.Rect(UI_MARGIN_X + BUTTON_W + UI_GAP_X, ui_buttons_y, BUTTON_W, BUTTON_H)
    btn_open_project = pygame.Rect(UI_MARGIN_X, ui_buttons_y + BUTTON_H + UI_GAP_X, BUTTON_W, BUTTON_H)

    # ------------------------------------------------------------
    # ✅ Список проектов (интерактивный)
    # ------------------------------------------------------------

    selected_project_index: int | None = None  # 🧠 ЛОГИКА: выбранный индекс в all_projects

    # 🖱️🖱️ ЛОГИКА: double click
    last_click_time = 0                 # 🧠 ЛОГИКА: время последнего клика (ms)
    last_click_index: int | None = None # 🧠 ЛОГИКА: индекс последнего клика

    DOUBLE_CLICK_MS = 350  # 🔧 МОЖНО МЕНЯТЬ: окно двойного клика (ms)

    # 🎨 UI списка проектов
    PROJECT_LIST_X = UI_MARGIN_X  # 🔧 МОЖНО МЕНЯТЬ
    PROJECT_LIST_Y = 240          # 🔧 МОЖНО МЕНЯТЬ
    PROJECT_ITEM_W = 420          # 🔧 МОЖНО МЕНЯТЬ
    PROJECT_ITEM_H = 36           # 🔧 МОЖНО МЕНЯТЬ
    PROJECT_ITEM_GAP = 8          # 🔧 МОЖНО МЕНЯТЬ

    # 🎞️ Анимация кнопки удаления
    DELETE_PULSE_SPEED = 3.2      # 🔧 МОЖНО МЕНЯТЬ: скорость пульсации
    DELETE_PULSE_ADD = (90, 30, 30)  # 🔧 МОЖНО МЕНЯТЬ: насколько “подсвечивать” (RGB добавка)

    def _get_delete_button_rect(selected_index: int) -> pygame.Rect:
        """
        🧠 ЛОГИКА: кнопка удаления всегда рядом с выбранной строкой.
        """
        y = PROJECT_LIST_Y + selected_index * (PROJECT_ITEM_H + PROJECT_ITEM_GAP)
        return pygame.Rect(
            UI_MARGIN_X + PROJECT_ITEM_W + UI_GAP_X,  # справа от списка
            y,                                        # на уровне выбранного проекта
            BUTTON_W,
            BUTTON_H,
        )

    running = True
    while running:
        clock.tick(fps)
        mouse_pos = pygame.mouse.get_pos()

        # ✅ список проектов (реестр)
        all_projects = list_all_projects()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # --- Создать проект ---
                if btn_create.collidepoint(mouse_pos):
                    project_location = filedialog.askdirectory(title="Выберите папку для проекта")
                    if project_location:
                        project_name = simpledialog.askstring("Имя проекта", "Введите имя проекта:")
                        if project_name:
                            created = create_project(Path(project_location), project_name)
                            if created is None:
                                status_message = "Ошибка: проект уже существует."
                            else:
                                status_message = f"Проект '{created.name}' создан."
                                print(f"Открытие стартовой сцены: {created.start_scene}")

                                if created.start_scene and check_scene_file(created.start_scene):
                                    run_scene_editor(created.start_scene, window_width, window_height, fps)
                                    running = False

                # --- Последний проект ---
                if btn_last_project.collidepoint(mouse_pos):
                    print("Клик по кнопке 'Последний проект'")
                    info = open_last_project(projects_dir)  # ✅ last_project.json -> fallback витрина
                    if info is None:
                        status_message = "Последний проект не найден."
                    else:
                        status_message = f"Открываем: {info.name}"
                        print(f"Стартовая сцена: {info.start_scene}")

                        # ✅ РЕЕСТР + LAST
                        register_project(info.root)
                        save_last_project(info.root)

                        if check_scene_file(info.start_scene):
                            run_scene_editor(info.start_scene, window_width, window_height, fps)
                            running = False

                # --- Открыть проект ---
                if btn_open_project.collidepoint(mouse_pos):
                    print("Клик по кнопке 'Открыть проект'")
                    project_root = open_selected_project()
                    if project_root:
                        info = open_project_by_path(project_root)
                        if info is None:
                            status_message = "Ошибка: project.json не найден в выбранной папке."
                        else:
                            status_message = f"Проект '{info.name}' открыт."

                            # ✅ РЕЕСТР + LAST
                            register_project(info.root)
                            save_last_project(info.root)

                            if check_scene_file(info.start_scene):
                                run_scene_editor(info.start_scene, window_width, window_height, fps)
                                running = False

                # ------------------------------------------------------------
                # 🖱️ Клик по проектам (выделение + двойной клик открыть)
                # ------------------------------------------------------------
                clicked_index: int | None = None
                y = PROJECT_LIST_Y

                for i, p in enumerate(all_projects):
                    item_rect = pygame.Rect(PROJECT_LIST_X, y, PROJECT_ITEM_W, PROJECT_ITEM_H)

                    if item_rect.collidepoint(mouse_pos):
                        clicked_index = i
                        break

                    y += PROJECT_ITEM_H + PROJECT_ITEM_GAP

                if clicked_index is not None:
                    # ✅ выделяем проект
                    selected_project_index = clicked_index

                    # ✅ проверяем двойной клик
                    now_ms = pygame.time.get_ticks()
                    is_double_click = (
                        last_click_index == clicked_index
                        and (now_ms - last_click_time) <= DOUBLE_CLICK_MS
                    )

                    last_click_index = clicked_index
                    last_click_time = now_ms

                    # 🖱️🖱️ двойной клик → открыть проект
                    if is_double_click:
                        info = all_projects[clicked_index]

                        # ✅ РЕЕСТР + LAST
                        register_project(info.root)
                        save_last_project(info.root)

                        if check_scene_file(info.start_scene):
                            run_scene_editor(info.start_scene, window_width, window_height, fps)
                            running = False

                # ------------------------------------------------------------
                # 🗑 Удалить выделенный проект (кнопка рядом с выбранным)
                # + подтверждение
                # ------------------------------------------------------------
                if selected_project_index is not None and 0 <= selected_project_index < len(all_projects):
                    delete_rect = _get_delete_button_rect(selected_project_index)

                    if delete_rect.collidepoint(mouse_pos):
                        info = all_projects[selected_project_index]

                        # ✅ Подтверждение удаления
                        confirm = messagebox.askyesno(
                            "Удаление проекта",
                            f"Удалить проект '{info.name}'?\n\nПапка будет удалена полностью:\n{info.root}"
                        )

                        if confirm:
                            ok = delete_project(info.root)

                            if ok:
                                status_message = f"Проект '{info.name}' удалён."
                                selected_project_index = None
                                last_click_index = None
                                last_click_time = 0
                            else:
                                status_message = "Ошибка: проект не найден для удаления."
                        else:
                            status_message = "Удаление отменено."

        # --- РЕНДЕР ---
        screen.fill(EDITOR_BG_COLOR)

        # Заголовок
        title_w = title_font.size(title_text)[0]
        title_x = (window_width - title_w) // 2
        title_y = TITLE_Y
        screen.blit(title_font.render(title_text, True, EDITOR_TEXT_COLOR), (title_x, title_y))

        # Строка "Менеджер проектов:"
        screen.blit(
            font.render("Менеджер проектов:", True, EDITOR_TEXT_COLOR),
            (UI_MARGIN_X, manager_y)
        )

        # Кнопки
        _draw_button(screen, font, btn_create, "Создать проект", mouse_pos)
        _draw_button(screen, font, btn_last_project, "Последний проект", mouse_pos)
        _draw_button(screen, font, btn_open_project, "Открыть проект", mouse_pos)

        # ------------------------------------------------------------
        # ✅ Список проектов (интерактивный)
        # ------------------------------------------------------------
        screen.blit(
            font.render("Проекты:", True, EDITOR_TEXT_COLOR),
            (PROJECT_LIST_X, PROJECT_LIST_Y - 30)  # 🔧 МОЖНО МЕНЯТЬ: отступ заголовка
        )

        y = PROJECT_LIST_Y
        if all_projects:
            for i, p in enumerate(all_projects):
                item_rect = pygame.Rect(PROJECT_LIST_X, y, PROJECT_ITEM_W, PROJECT_ITEM_H)

                # фон строки
                if selected_project_index == i:
                    pygame.draw.rect(screen, (70, 100, 160), item_rect)  # 🔧 МОЖНО МЕНЯТЬ: цвет выделения
                else:
                    pygame.draw.rect(screen, (40, 40, 46), item_rect)    # 🔧 МОЖНО МЕНЯТЬ: обычный фон

                # рамка строки
                pygame.draw.rect(screen, BUTTON_BORDER_COLOR, item_rect, 1)

                # текст проекта
                screen.blit(
                    font.render(p.name, True, EDITOR_TEXT_COLOR),
                    (item_rect.x + 10, item_rect.y + 6)  # 🔧 МОЖНО МЕНЯТЬ: паддинги текста
                )

                y += PROJECT_ITEM_H + PROJECT_ITEM_GAP
        else:
            _draw_lines(
                screen,
                font,
                ["(пока пусто)"],
                x=PROJECT_LIST_X,
                y=PROJECT_LIST_Y,
                color=EDITOR_TEXT_COLOR
            )

        # ------------------------------------------------------------
        # ✅ Кнопка удаления (рядом с выбранным) + плавная подсветка
        # ------------------------------------------------------------
        if selected_project_index is not None and 0 <= selected_project_index < len(all_projects):
            delete_rect = _get_delete_button_rect(selected_project_index)

            # 🎞️ Пульсация: 0..1..0
            t = pygame.time.get_ticks() / 1000.0  # секунды
            pulse = (math.sin(t * DELETE_PULSE_SPEED) + 1.0) * 0.5  # 0..1

            # фон кнопки: берём базовый и добавляем подсветку
            base_bg = BUTTON_BG_COLOR
            pulse_bg = _blend_color(base_bg, DELETE_PULSE_ADD, pulse)

            # hover усиливает подсветку
            is_hover = delete_rect.collidepoint(mouse_pos)
            if is_hover:
                pulse_bg = _blend_color(pulse_bg, (50, 20, 20), 1.0)  # 🔧 МОЖНО МЕНЯТЬ

            pygame.draw.rect(screen, pulse_bg, delete_rect)
            pygame.draw.rect(screen, BUTTON_BORDER_COLOR, delete_rect, BUTTON_BORDER_WIDTH)

            label = font.render("Удалить проект", True, BUTTON_TEXT_COLOR)
            screen.blit(label, label.get_rect(center=delete_rect.center))

        # Статус
        if status_message:
            _draw_lines(screen, font, [status_message], x=UI_MARGIN_X, y=550, color=EDITOR_HINT_COLOR)

        pygame.display.flip()

    pygame.quit()


# ============================================================
# ✅ ПУБЛИЧНЫЙ API ДЛЯ engine_main.py (совместимость, НЕ UI)
# ============================================================
def run_editor(*args, **kwargs):
    """
    🧠 ЛОГИКА: адаптер аргументов (UI НЕ МЕНЯЕМ).

    Поддерживает варианты вызова:
      1) run_editor(w, h, title, fps, projects_dir)
      2) run_editor(window_width=..., window_height=..., window_title=..., fps=..., projects_dir=...)
      3) run_editor({...})  # один dict параметров
      4) другие имена ключей: width/height/title/FPS и т.д.
    """

    # ✅ Случай: один dict позиционно: run_editor(config_dict)
    if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
        kwargs = dict(args[0])
        args = ()

    # ✅ Случай: позиционные аргументы
    if args and len(args) >= 5:
        return _run_editor_impl(*args[:5])

    # ✅ helper: выбрать первое найденное имя ключа
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

    # ✅ Fallback: если часть параметров не передали, берём дефолты
    try:
        from config_engine import WINDOW_WIDTH as _DW, WINDOW_HEIGHT as _DH, FPS as _DFPS
    except Exception:
        _DW, _DH, _DFPS = 1280, 720, 60  # 🔧 МОЖНО МЕНЯТЬ, но лучше задать в config_engine

    if window_width is None:
        window_width = _DW
    if window_height is None:
        window_height = _DH
    if fps is None:
        fps = _DFPS
    if window_title is None:
        window_title = "DragonEngine"
    if projects_dir is None:
        # 🔧 МОЖНО МЕНЯТЬ: дефолтная папка "projects" рядом с репозиторием
        projects_dir = (Path(__file__).resolve().parents[1] / "projects")

    # ✅ Нормализуем projects_dir в Path
    if not isinstance(projects_dir, Path):
        projects_dir = Path(str(projects_dir))

    return _run_editor_impl(
        window_width=int(window_width),
        window_height=int(window_height),
        window_title=str(window_title),
        fps=int(fps),
        projects_dir=projects_dir,
    )
