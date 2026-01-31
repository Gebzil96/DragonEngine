import os  # ✅ НОВОЕ: фиксация позиции окна SDL
import pygame  # 🧠 ЛОГИКА: для рисования и обработки событий
import json  # 🧠 ЛОГИКА: для загрузки/сохранения сцены
from pathlib import Path  # 🧠 ЛОГИКА: для путей

from engine.config_engine import (  # 🔧 МОЖНО МЕНЯТЬ: цвета и шрифты
    EDITOR_BG_COLOR,
    EDITOR_TEXT_COLOR,
    FONT_SIZE,
)

from engine_settings import load_settings, save_settings  # ✅ настройки движка

# ============================================================
# ✅ ПРОЕКТ: имя проекта по scene_path -> project.json
# ============================================================
def _get_project_name_from_scene_path(scene_path: Path) -> str:
    """
    🧠 ЛОГИКА:
    Определяем имя проекта по пути сцены:
      .../<project_root>/scenes/<scene>.scene.json

    1) project_root = scene_path.parent.parent
    2) читаем project.json и берём поле "name"
    3) fallback: имя папки project_root
    """
    try:
        project_root = scene_path.resolve().parent.parent
        project_json = project_root / "project.json"

        if project_json.exists():
            with open(project_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            name = data.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()

        return project_root.name
    except Exception:
        return "Проект"


def load_scene(scene_path: Path):
    """🧠 ЛОГИКА: загрузка сцены из файла JSON."""
    if scene_path.exists():
        with open(scene_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return {"name": "main", "entities": []}  # 🧠 ЛОГИКА: если сцена не существует


def save_scene(scene_path: Path, scene_data):
    """🧠 ЛОГИКА: сохраняет изменённую сцену в файл."""
    with open(scene_path, "w", encoding="utf-8") as file:
        json.dump(scene_data, file, ensure_ascii=False, indent=2)


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


def _draw_project_badge(screen, font, project_name: str) -> pygame.Rect:
    """
    🧠 ЛОГИКА:
    Рисуем имя проекта слева сверху.
    Возвращаем rect бейджа (иногда удобно для выравнивания).
    """
    BADGE_X = 10  # 🔧 МОЖНО МЕНЯТЬ
    BADGE_Y = 10  # 🔧 МОЖНО МЕНЯТЬ
    PAD_X = 10    # 🔧 МОЖНО МЕНЯТЬ
    PAD_Y = 6     # 🔧 МОЖНО МЕНЯТЬ

    TEXT_COLOR = EDITOR_TEXT_COLOR  # 🔧 МОЖНО МЕНЯТЬ
    BG_COLOR = (20, 20, 24)         # 🔧 МОЖНО МЕНЯТЬ
    BORDER_COLOR = (80, 80, 92)     # 🔧 МОЖНО МЕНЯТЬ
    BORDER_W = 1                    # 🔧 МОЖНО МЕНЯТЬ
    RADIUS = 8                      # 🔧 МОЖНО МЕНЯТЬ

    text = f"Проект: {project_name}"
    surf = font.render(text, True, TEXT_COLOR)
    rect = surf.get_rect(topleft=(BADGE_X + PAD_X, BADGE_Y + PAD_Y))

    bg_rect = pygame.Rect(
        BADGE_X,
        BADGE_Y,
        rect.width + PAD_X * 2,
        rect.height + PAD_Y * 2,
    )

    pygame.draw.rect(screen, BG_COLOR, bg_rect, border_radius=RADIUS)
    pygame.draw.rect(screen, BORDER_COLOR, bg_rect, BORDER_W, border_radius=RADIUS)
    screen.blit(surf, rect)

    return bg_rect


# ============================================================
# ✅ КНОПКА "К проектам" (правый верхний угол, компактная)
# ============================================================
def _get_back_button_rect(window_width: int) -> pygame.Rect:
    """
    🧠 ЛОГИКА:
    Единое место, где вычисляем rect кнопки — чтобы:
    - не рисовать кнопку во время обработки событий
    - одинаково работали клики и рендер

    🔧 МОЖНО МЕНЯТЬ:
    - размеры и отступы
    """
    MARGIN = 10  # 🔧 МОЖНО МЕНЯТЬ
    BTN_W = 150  # 🔧 МОЖНО МЕНЯТЬ (меньше)
    BTN_H = 28   # 🔧 МОЖНО МЕНЯТЬ (меньше)

    x = window_width - BTN_W - MARGIN
    y = MARGIN
    return pygame.Rect(x, y, BTN_W, BTN_H)


def _draw_back_button(screen, font, mouse_pos, window_width: int) -> tuple[pygame.Rect, bool]:
    """
    🧠 ЛОГИКА:
    Кнопка возврата в менеджер проектов.
    Возвращаем (rect, is_hover).

    🔧 МОЖНО МЕНЯТЬ:
    - цвета/рамку/скругление
    - текст
    """
    BG = (35, 35, 40)        # 🔧 МОЖНО МЕНЯТЬ
    BG_HOVER = (55, 55, 64)  # 🔧 МОЖНО МЕНЯТЬ
    BORDER = (90, 90, 105)   # 🔧 МОЖНО МЕНЯТЬ
    BORDER_W = 1             # 🔧 МОЖНО МЕНЯТЬ
    RADIUS = 8               # 🔧 МОЖНО МЕНЯТЬ

    text = "К проектам"  # ✅ без стрелки (убрали “квадратик”)

    rect = _get_back_button_rect(window_width)
    is_hover = rect.collidepoint(mouse_pos)

    pygame.draw.rect(screen, BG_HOVER if is_hover else BG, rect, border_radius=RADIUS)
    pygame.draw.rect(screen, BORDER, rect, BORDER_W, border_radius=RADIUS)

    label = font.render(text, True, EDITOR_TEXT_COLOR)
    screen.blit(label, label.get_rect(center=rect.center))

    return rect, is_hover


# ============================================================
# ✅ FULLSCREEN / BORDERLESS DETECT
# ============================================================
def _get_current_display_mode() -> str:
    """
    🧠 ЛОГИКА:
    Определяем режим окна, который уже выставил менеджер проектов.
    Возвращаем: "fullscreen" | "borderless" | "windowed"
    """
    surf = pygame.display.get_surface()
    if surf is None:
        return "windowed"

    flags = surf.get_flags()

    if flags & pygame.FULLSCREEN:
        return "fullscreen"

    # Borderless fullscreen: NOFRAME + размер как у дисплея
    if flags & pygame.NOFRAME:
        try:
            info = pygame.display.Info()
            w, h = surf.get_size()
            if w == info.current_w and h == info.current_h:
                return "borderless"
        except Exception:
            pass

    return "windowed"


def run_scene_editor(scene_path, window_width, window_height, fps):
    """
    🧠 ЛОГИКА: основной цикл редактора сцены.

    Важно:
    - НЕ вызываем pygame.quit() здесь (чтобы не убить display у editor_app)
    - Возвращаем код выхода:
        "quit" — пользователь закрыл окно крестиком (закрываем весь движок)
        "back" — пользователь нажал кнопку "К проектам" (возврат в менеджер)
    """

    # ✅ SDL читает позицию окна при создании.
    os.environ["SDL_VIDEO_CENTERED"] = "0"
    os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"

    pygame.display.set_caption("Редактор сцены")

    mode = _get_current_display_mode()

    if mode == "fullscreen":
        flags = pygame.FULLSCREEN
        screen = pygame.display.set_mode((0, 0), flags)
    elif mode == "borderless":
        info = pygame.display.Info()
        flags = pygame.NOFRAME
        screen = pygame.display.set_mode((info.current_w, info.current_h), flags)
    else:
        flags = 0
        screen = pygame.display.set_mode((window_width, window_height), flags)

    # ✅ Важно: обновляем реальные размеры (в fullscreen/borderless они будут нативными)
    window_width, window_height = screen.get_size()

    clock = pygame.time.Clock()

    font = pygame.font.SysFont(None, FONT_SIZE)
    scene_path = Path(scene_path)
    scene_data = load_scene(scene_path)
    selected_entity = None

    project_name = _get_project_name_from_scene_path(scene_path)

    engine_settings = load_settings()
    engine_settings.setdefault("debug_overlay", False)
    settings_open = False

    running = True
    while running:
        clock.tick(fps)
        mouse_pos = pygame.mouse.get_pos()

        # ✅ На случай смены разрешения/режима — берём актуальный размер
        window_width, window_height = screen.get_size()

        back_btn_rect = _get_back_button_rect(window_width)

        # ====================================================
        # ✅ новые кнопки сцены
        # ====================================================
        BTN_W = 120  # 🔧 МОЖНО МЕНЯТЬ
        BTN_H = 28   # 🔧 МОЖНО МЕНЯТЬ
        MARGIN = 10  # 🔧 МОЖНО МЕНЯТЬ

        settings_rect = pygame.Rect(
            window_width - BTN_W * 2 - MARGIN * 2,
            MARGIN,
            BTN_W,
            BTN_H,
        )

        exit_rect = pygame.Rect(
            window_width - BTN_W - MARGIN,
            MARGIN,
            BTN_W,
            BTN_H,
        )

        # --- СОБЫТИЯ ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

                 # ✅ Выход из движка
                if exit_rect.collidepoint(event.pos):
                    return "quit"

                # ✅ открыть/закрыть настройки
                if settings_rect.collidepoint(event.pos):
                    settings_open = not settings_open
                    continue

                # ✅ Клик по кнопке "К проектам"
                if back_btn_rect.collidepoint(event.pos):
                    return "back"

                # ✅ Выбор сущности
                for entity in scene_data.get("entities", []):
                    if entity.get("type") != "rect":
                        continue
                    rect = pygame.Rect(entity["x"], entity["y"], entity["w"], entity["h"])
                    if rect.collidepoint(mouse_pos):
                        selected_entity = entity

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                selected_entity = None

        # --- РЕНДЕР ---
        screen.fill(EDITOR_BG_COLOR)

        # ✅ Бейдж проекта слева сверху
        _draw_project_badge(screen, font, project_name)

        # ✅ Кнопка "К проектам" справа сверху (компактная)
        _draw_back_button(screen, font, mouse_pos, window_width)

         # ==============================
        # ✅ кнопка Настройки
        # ==============================
        pygame.draw.rect(screen, (40,40,46), settings_rect, border_radius=6)
        pygame.draw.rect(screen, (90,90,100), settings_rect, 1, border_radius=6)
        label = font.render("Настройки", True, EDITOR_TEXT_COLOR)
        screen.blit(label, label.get_rect(center=settings_rect.center))

        # ==============================
        # ✅ кнопка Выход
        # ==============================
        pygame.draw.rect(screen, (120,45,45), exit_rect, border_radius=6)
        pygame.draw.rect(screen, (150,70,70), exit_rect, 1, border_radius=6)
        label = font.render("Выход", True, EDITOR_TEXT_COLOR)
        screen.blit(label, label.get_rect(center=exit_rect.center))

        draw_entities(screen, scene_data.get("entities", []), font)

        if selected_entity:
            handle_entity_move(mouse_pos, selected_entity)

        # ====================================================
        # ✅ панель настроек сцены
        # ====================================================
        if settings_open:
            panel = pygame.Rect(20, 60, 260, 90)

            pygame.draw.rect(screen, (30,30,36), panel, border_radius=8)
            pygame.draw.rect(screen, (90,90,100), panel, 1, border_radius=8)

            text = font.render("Debug overlay", True, EDITOR_TEXT_COLOR)
            screen.blit(text, (panel.x + 40, panel.y + 30))

            checkbox = pygame.Rect(panel.x + 10, panel.y + 30, 20, 20)
            pygame.draw.rect(screen, (80,80,90), checkbox, 2)

            if engine_settings["debug_overlay"]:
                pygame.draw.line(screen, (120,220,120), checkbox.topleft, checkbox.bottomright, 3)
                pygame.draw.line(screen, (120,220,120), checkbox.topright, checkbox.bottomleft, 3)

            # клик по чекбоксу
            if pygame.mouse.get_pressed()[0] and checkbox.collidepoint(mouse_pos):
                engine_settings["debug_overlay"] = not engine_settings["debug_overlay"]
                save_settings(engine_settings)
                pygame.time.delay(150)

        if engine_settings["debug_overlay"]:
            dbg = [
                f"FPS: {clock.get_fps():.1f}",
                f"Mouse: {mouse_pos}",
                f"Entities: {len(scene_data.get('entities', []))}",
            ]

            y = 120
            for line in dbg:
                surf = font.render(line, True, (220,220,60))
                screen.blit(surf, (10, y))
                y += 20

        pygame.display.flip()

        # --- СОХРАНЕНИЕ СЦЕНЫ ---
        if pygame.key.get_pressed()[pygame.K_s]:
            save_scene(scene_path, scene_data)

    return "back"
