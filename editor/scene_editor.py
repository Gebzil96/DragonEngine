import pygame  # 🧠 ЛОГИКА: для рисования и обработки событий
import json  # 🧠 ЛОГИКА: для загрузки/сохранения сцены
from pathlib import Path  # 🧠 ЛОГИКА: для путей

from engine.config_engine import (  # 🔧 МОЖНО МЕНЯТЬ: цвета и шрифты
    EDITOR_BG_COLOR,
    EDITOR_TEXT_COLOR,
    FONT_SIZE,
)

def load_scene(scene_path: Path):
    """🧠 ЛОГИКА: загрузка сцены из файла JSON."""
    if scene_path.exists():
        with open(scene_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {"name": "main", "entities": []}  # 🧠 ЛОГИКА: если сцена не существует

def save_scene(scene_path: Path, scene_data):
    """🧠 ЛОГИКА: сохраняет изменённую сцену в файл."""
    with open(scene_path, 'w', encoding='utf-8') as file:
        json.dump(scene_data, file, ensure_ascii=False, indent=2)

def draw_entities(screen, entities, font):
    """🧠 ЛОГИКА: рисует все сущности на экране."""
    for entity in entities:
        if entity['type'] == 'rect':
            pygame.draw.rect(
                screen,
                (255, 255, 255),  # 🧠 ЛОГИКА: белый квадрат (можно сделать цветом из сцены)
                (entity['x'], entity['y'], entity['w'], entity['h'])
            )
            # 🧠 ЛОГИКА: рисуем идентификатор сущности (для отображения)
            label = font.render(entity['id'], True, EDITOR_TEXT_COLOR)
            screen.blit(label, (entity['x'], entity['y'] - 20))  # 🧠 ЛОГИКА: немного выше квадрата

def handle_entity_move(entities, mouse_pos, selected_entity):
    """🧠 ЛОГИКА: если выбрана сущность, она двигается за мышью."""
    if selected_entity:
        selected_entity['x'], selected_entity['y'] = mouse_pos  # 🧠 ЛОГИКА: перемещаем сущность

def run_scene_editor(scene_path, window_width, window_height, fps):
    """🧠 ЛОГИКА: основной цикл редактора сцены."""
    pygame.init()  # 🧠 ЛОГИКА: инициализация pygame

    screen = pygame.display.set_mode((window_width, window_height))  # 🧠 ЛОГИКА: создаём окно
    pygame.display.set_caption("Редактор сцены")  # 🧠 ЛОГИКА: заголовок окна
    
    font = pygame.font.SysFont(None, FONT_SIZE)  # 🧠 ЛОГИКА: шрифт для текста
    scene_data = load_scene(scene_path)  # 🧠 ЛОГИКА: загрузка сцены
    selected_entity = None  # 🧠 ЛОГИКА: сущность, которая выбрана для перемещения

    running = True  # 🧠 ЛОГИКА: главный цикл редактора
    while running:
        mouse_pos = pygame.mouse.get_pos()  # 🧠 ЛОГИКА: положение мыши
        
        # --- СОБЫТИЯ ---
        for event in pygame.event.get():  # 🧠 ЛОГИКА: очередь событий
            if event.type == pygame.QUIT:  # 🧠 ЛОГИКА: закрытие окна
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # 🧠 ЛОГИКА: левая кнопка мыши
                for entity in scene_data['entities']:
                    rect = pygame.Rect(entity['x'], entity['y'], entity['w'], entity['h'])
                    if rect.collidepoint(mouse_pos):
                        selected_entity = entity  # 🧠 ЛОГИКА: выбрали сущность для перемещения

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:  # 🧠 ЛОГИКА: отпустили кнопку
                selected_entity = None  # 🧠 ЛОГИКА: убираем выбор сущности

        # --- РЕНДЕР ---
        screen.fill(EDITOR_BG_COLOR)  # 🧠 ЛОГИКА: фон редактора

        # 🧠 ЛОГИКА: рисуем сущности
        draw_entities(screen, scene_data['entities'], font)

        # 🧠 ЛОГИКА: перетаскивание сущности
        if selected_entity:
            handle_entity_move(scene_data['entities'], mouse_pos, selected_entity)

        pygame.display.flip()  # 🧠 ЛОГИКА: показываем кадр

        # --- СОХРАНЕНИЕ СЦЕНЫ ---
        if pygame.key.get_pressed()[pygame.K_s]:  # 🧠 ЛОГИКА: сохраняем при нажатии S
            save_scene(scene_path, scene_data)

    pygame.quit()  # 🧠 ЛОГИКА: корректное завершение
