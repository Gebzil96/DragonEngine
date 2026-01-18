import sys
import pygame
import tkinter as tk
from tkinter import simpledialog, filedialog
from pathlib import Path
import json

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
    BUTTON_W,          # добавлено
    BUTTON_H,          # добавлено
    ENGINE_VERSION,    # добавлено
    DEFAULT_SCENE_NAME,# добавлено
    EDITOR_HINT_COLOR, # добавлено
    EDITOR_BG_COLOR,
    EDITOR_TEXT_COLOR,
)

from project_manager import (
    list_all_projects,     # ✅ ВСЕ проекты из реестра
    register_project,      # ✅ регистрируем любой созданный/открытый проект
    open_last_project,
    save_last_project,
    open_project_by_path,
)
from editor.scene_editor import run_scene_editor  # 🧠 ЛОГИКА: редактор сцены


# 🧠 ЛОГИКА: tkinter нужен только для диалогов
root = tk.Tk()
root.withdraw()


class Project:
    """🧠 ЛОГИКА: локальный класс проекта (используется при создании)."""
    def __init__(self, path: Path, name: str):
        self.root = path                 # 🧠 ЛОГИКА: корневая папка проекта
        self.name = name                 # 🧠 ЛОГИКА: имя проекта
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


def run_editor(window_width: int, window_height: int, window_title: str, fps: int, projects_dir: Path):
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

    running = True
    while running:
        clock.tick(fps)
        mouse_pos = pygame.mouse.get_pos()

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

        # ✅ ВСЕ проекты из реестра projects_index.json
        all_projects = list_all_projects()
        projects_lines = ["Проекты:"]

        if all_projects:
            for p in all_projects:
                projects_lines.append(f"- {p.name}")
        else:
            projects_lines.append("(пока пусто)")

        _draw_lines(screen, font, projects_lines, x=UI_MARGIN_X, y=240, color=EDITOR_TEXT_COLOR)

        # Статус
        if status_message:
            _draw_lines(screen, font, [status_message], x=UI_MARGIN_X, y=550, color=EDITOR_HINT_COLOR)

        pygame.display.flip()

    pygame.quit()
