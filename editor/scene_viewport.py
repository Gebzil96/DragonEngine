# editor/scene_viewport.py
from __future__ import annotations

import pygame


class SceneViewport:
    """
    🧠 ЛОГИКА:
    Viewport — отдельная область внутри окна редактора, где:
    - рисуем "мир" (сетку, сущности)
    - выбираем сущности
    - перетаскиваем сущности
    - делаем преобразование screen <-> world

    Сейчас камера = простое смещение (cam_x/cam_y), zoom пока не нужен.
    """

    def __init__(self, rect: pygame.Rect):
        self.rect = rect

        # ----------------
        # 🔧 МОЖНО МЕНЯТЬ
        # ----------------
        self.grid_step = 32
        self.grid_alpha = 60
        self.bg = (18, 19, 26)
        self.border = (120, 130, 170)

        # Камера (world offset)
        self.cam_x = 0.0
        self.cam_y = 0.0

        # Drag state
        self.selected_entity: dict | None = None
        self._dragging = False
        self._grab_dx = 0.0
        self._grab_dy = 0.0

    def set_rect(self, rect: pygame.Rect) -> None:
        self.rect = rect

    # -----------------------------
    # Coords
    # -----------------------------
    def screen_to_world(self, screen_pos: tuple[int, int]) -> tuple[float, float]:
        sx, sy = screen_pos
        wx = (sx - self.rect.x) + self.cam_x
        wy = (sy - self.rect.y) + self.cam_y
        return wx, wy

    def world_to_screen(self, world_pos: tuple[float, float]) -> tuple[int, int]:
        wx, wy = world_pos
        sx = int((wx - self.cam_x) + self.rect.x)
        sy = int((wy - self.cam_y) + self.rect.y)
        return sx, sy

    def contains(self, screen_pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(screen_pos)

    # -----------------------------
    # Picking / dragging
    # -----------------------------
    def _entity_world_rect(self, ent: dict) -> pygame.Rect:
        return pygame.Rect(int(ent["x"]), int(ent["y"]), int(ent["w"]), int(ent["h"]))

    def _entity_screen_rect(self, ent: dict) -> pygame.Rect:
        wx = float(ent["x"])
        wy = float(ent["y"])
        ww = int(ent["w"])
        wh = int(ent["h"])
        sx, sy = self.world_to_screen((wx, wy))
        return pygame.Rect(sx, sy, ww, wh)

    def pick_entity(self, screen_pos: tuple[int, int], entities: list[dict]) -> dict | None:
        """
        🧠 ЛОГИКА:
        Выбор сущности только внутри viewport.
        Приоритет: сущности “выше” (последние в списке).
        """
        if not self.contains(screen_pos):
            return None

        for ent in reversed(entities):
            if ent.get("type") != "rect":
                continue
            r = self._entity_screen_rect(ent)
            if r.collidepoint(screen_pos):
                return ent
        return None

    def start_drag(self, ent: dict, screen_pos: tuple[int, int]) -> None:
        if ent is None:
            return

        self.selected_entity = ent
        wx, wy = self.screen_to_world(screen_pos)

        ex = float(ent["x"])
        ey = float(ent["y"])
        self._grab_dx = wx - ex
        self._grab_dy = wy - ey

        self._dragging = True

    def drag_to(self, screen_pos: tuple[int, int]) -> None:
        if not self._dragging or not self.selected_entity:
            return
        wx, wy = self.screen_to_world(screen_pos)
        self.selected_entity["x"] = int(wx - self._grab_dx)
        self.selected_entity["y"] = int(wy - self._grab_dy)

    def end_drag(self) -> None:
        self._dragging = False

    def clear_selection(self) -> None:
        self.selected_entity = None
        self._dragging = False

    # -----------------------------
    # Render
    # -----------------------------
    def _draw_grid(self, surf: pygame.Surface) -> None:
        # сетка рисуется только внутри viewport через clip
        w = self.rect.width
        h = self.rect.height
        if w <= 0 or h <= 0:
            return

        # стартовые линии с учётом камеры
        # (cam_x/cam_y — в world, значит сдвиг влияет на видимую сетку)
        step = max(8, int(self.grid_step))

        offset_x = int((-self.cam_x) % step)
        offset_y = int((-self.cam_y) % step)

        grid_color = (255, 255, 255, int(self.grid_alpha))
        grid_surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # vertical
        x = offset_x
        while x < w:
            pygame.draw.line(grid_surf, grid_color, (x, 0), (x, h), 1)
            x += step

        # horizontal
        y = offset_y
        while y < h:
            pygame.draw.line(grid_surf, grid_color, (0, y), (w, y), 1)
            y += step

        surf.blit(grid_surf, (self.rect.x, self.rect.y))

    def draw(
        self,
        screen: pygame.Surface,
        entities: list[dict],
        font: pygame.font.Font,
        text_color: tuple[int, int, int],
    ) -> None:
        # фон viewport
        pygame.draw.rect(screen, self.bg, self.rect)

        # ограничиваем рисование только viewport
        prev_clip = screen.get_clip()
        screen.set_clip(self.rect)

        # сетка
        self._draw_grid(screen)

        # сущности
        for ent in entities:
            if ent.get("type") != "rect":
                continue

            r = self._entity_screen_rect(ent)

            # базовый прямоугольник
            pygame.draw.rect(screen, (235, 235, 240), r, 0)

            # id/label
            label = font.render(str(ent.get("id", "")), True, text_color)
            screen.blit(label, (r.x, r.y - 18))

            # обводка выбранного
            if self.selected_entity is ent:
                pygame.draw.rect(screen, (255, 210, 120), r, 2)

        # возвращаем clip
        screen.set_clip(prev_clip)

        # рамка viewport (уже вне clip — чтобы была всегда видна)
        pygame.draw.rect(screen, self.border, self.rect, 1)
