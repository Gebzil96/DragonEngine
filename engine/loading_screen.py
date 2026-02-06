# engine/loading_screen.py
from __future__ import annotations

from dataclasses import dataclass

import pygame


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def draw_loading_overlay(
    screen: pygame.Surface,
    percent: float,
    text: str = "Загрузка…",
    subtext: str | None = None,
) -> None:
    """
    🧠 ЛОГИКА:
    Рисует загрузочный оверлей НА ТЕКУЩЕМ экране pygame (не создаёт новое окно).
    Безопасно использовать внутри editor_app.py перед запуском scene_editor.
    """
    percent = _clamp(float(percent), 0.0, 100.0)

    w, h = screen.get_size()

    # фон
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((10, 10, 14, 235))
    screen.blit(overlay, (0, 0))

    # шрифты
    title_font = pygame.font.Font(None, max(24, int(h * 0.07)))
    info_font = pygame.font.Font(None, max(18, int(h * 0.045)))

    # текст
    title_surf = title_font.render(text, True, (235, 235, 245))
    title_rect = title_surf.get_rect(center=(w // 2, int(h * 0.38)))
    screen.blit(title_surf, title_rect)

    if subtext:
        sub_surf = info_font.render(subtext, True, (170, 170, 185))
        sub_rect = sub_surf.get_rect(center=(w // 2, int(h * 0.45)))
        screen.blit(sub_surf, sub_rect)

    # полоса прогресса
    bar_w = int(w * 0.62)
    bar_h = max(18, int(h * 0.03))
    bar_x = (w - bar_w) // 2
    bar_y = int(h * 0.55)

    pygame.draw.rect(screen, (50, 50, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=10)

    fill_w = int(bar_w * (percent / 100.0))
    if fill_w > 0:
        pygame.draw.rect(screen, (120, 190, 255), (bar_x, bar_y, fill_w, bar_h), border_radius=10)

    pygame.draw.rect(screen, (170, 180, 220), (bar_x, bar_y, bar_w, bar_h), width=1, border_radius=10)

    # проценты
    pct_surf = info_font.render(f"{int(percent):d}%", True, (235, 235, 245))
    pct_rect = pct_surf.get_rect(center=(w // 2, int(h * 0.62)))
    screen.blit(pct_surf, pct_rect)


@dataclass
class LoadingScreen:
    """
    🧠 ЛОГИКА:
    Отдельное минимальное окно для загрузки (используем в engine_main.py до импортов).
    Потом закрываем и отдаём управление основному UI.
    """
    title: str = "DragonEngine"
    size: tuple[int, int] | None = None  # 🔧 МОЖНО МЕНЯТЬ: None = размер рабочего стола
    borderless: bool = True              # 🔧 МОЖНО МЕНЯТЬ: True = без рамки (быстрее/чище)

    def __post_init__(self) -> None:
        pygame.init()
        pygame.display.init()

        # ✅ вычисляем размер окна загрузки
        if self.size is None:
            w, h = 1280, 720  # fallback
            try:
                sizes = pygame.display.get_desktop_sizes()  # type: ignore[attr-defined]
                if sizes:
                    w, h = int(sizes[0][0]), int(sizes[0][1])
            except Exception:
                try:
                    info = pygame.display.Info()
                    if int(info.current_w) > 0 and int(info.current_h) > 0:
                        w, h = int(info.current_w), int(info.current_h)
                except Exception:
                    pass
            self.size = (w, h)

        flags = 0
        if self.borderless:
            flags |= pygame.NOFRAME

        self.screen = pygame.display.set_mode(self.size, flags)
        pygame.display.set_caption(self.title)
        self.clock = pygame.time.Clock()

        # первый кадр сразу
        self.update(0, "Загрузка…")

    def update(self, percent: float, text: str = "Загрузка…", subtext: str | None = None) -> None:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                # во время загрузки — просто игнорим закрытие (чтобы не ломать init)
                pass

        self.screen.fill((10, 10, 14))
        draw_loading_overlay(self.screen, percent, text=text, subtext=subtext)
        pygame.display.flip()

        self.clock.tick(60)

    def close(self) -> None:
        """
        🧠 ЛОГИКА:
        Не убиваем pygame/display, чтобы не было "дёрганого" перехода:
        splash остаётся последним кадром, а основной UI перерисует то же окно.
        """
        return