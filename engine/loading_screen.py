# engine/loading_screen.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame
import time

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

def draw_loading_badge(
    screen: pygame.Surface,
    percent: float,
    text: str = "Загрузка…",
    subtext: str | None = None,
) -> None:
    """
    🧠 ЛОГИКА:
    Мини-бейдж поверх уже нарисованного кадра (НЕ заливает весь экран),
    чтобы можно было показать 100% прямо на первом реальном кадре UI.
    """
    percent = _clamp(float(percent), 0.0, 100.0)
    w, h = screen.get_size()

    pad = max(10, int(min(w, h) * 0.015))
    bw = int(w * 0.34)
    bh = max(42, int(h * 0.085))
    x = (w - bw) // 2
    y = h - bh - int(h * 0.06)

    badge = pygame.Surface((bw, bh), pygame.SRCALPHA)
    badge.fill((10, 10, 14, 200))

    pygame.draw.rect(badge, (170, 180, 220, 220), (0, 0, bw, bh), width=1, border_radius=12)

    title_font = pygame.font.Font(None, max(20, int(h * 0.045)))
    info_font = pygame.font.Font(None, max(18, int(h * 0.040)))

    line1 = title_font.render(f"{text}  {int(percent):d}%", True, (235, 235, 245))
    badge.blit(line1, (pad, pad))

    if subtext:
        line2 = info_font.render(subtext, True, (170, 170, 185))
        badge.blit(line2, (pad, pad + line1.get_height() + 4))

    screen.blit(badge, (x, y))

def run_fade_transition(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    *,
    duration_ms: int = 140,     # 🔧 МОЖНО МЕНЯТЬ
    fade_out: bool = True,
    fade_in: bool = True,
) -> None:
    """
    Короткий fade, чтобы скрыть рывок пересоздания окна/смены режима.
    """
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)

    def _fade(a0: int, a1: int, ms: int) -> None:
        t0 = time.perf_counter()
        dur = max(0.001, ms / 1000.0)
        while True:
            now = time.perf_counter()
            k = (now - t0) / dur
            if k >= 1.0:
                k = 1.0

            a = int(a0 + (a1 - a0) * k)
            overlay.fill((0, 0, 0, a))

            pygame.event.pump()
            screen.blit(overlay, (0, 0))
            pygame.display.flip()
            clock.tick(120)

            if k >= 1.0:
                break

    if fade_out:
        _fade(0, 255, duration_ms)
    if fade_in:
        _fade(255, 0, duration_ms)

import json
from contextlib import contextmanager
from pathlib import Path


class LoadingProfiler:
    """
    "Честные проценты" по времени:
    - меряем perf_counter() в фазах
    - остаток времени оцениваем из профиля прошлых запусков
    - 100% показываем только когда реально готовы переходить дальше
    """

    # 🔧 МОЖНО МЕНЯТЬ: список фаз и базовые ожидания (секунды) для первого запуска
    DEFAULT_PHASES: list[tuple[str, float]] = [
        ("imports", 0.80),
        ("settings", 0.20),
        ("project_scan", 0.90),
        ("ui_boot", 0.70),
        ("first_frame", 0.35),
    ]

    def __init__(
        self,
        cache_path: str = "engine/.cache/loading_profile.json",  # 🔧 МОЖНО МЕНЯТЬ
        phases: list[tuple[str, float]] | None = None,
        ema_alpha: float = 0.35,  # 🔧 МОЖНО МЕНЯТЬ: 0..1 (выше = быстрее учится)
    ) -> None:
        self.ema_alpha = float(ema_alpha)
        self.phases = phases[:] if phases is not None else self.DEFAULT_PHASES[:]

        self.cache_path = Path(cache_path)
        self._expected = {k: float(v) for k, v in self.phases}
        self._actual: dict[str, float] = {}
        self._t0 = time.perf_counter()
        self._phase_t0: float | None = None
        self._phase_key: str | None = None

        self._load_cache()

    def _load_cache(self) -> None:
        try:
            if not self.cache_path.exists():
                return
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if k in self._expected and isinstance(v, (int, float)) and v > 0:
                        self._expected[k] = float(v)
        except Exception:
            # cache повреждён — игнорируем
            pass

    def _save_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self._expected, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def begin_phase(self, key: str) -> None:
        self._phase_key = key
        self._phase_t0 = time.perf_counter()

    def end_phase(self) -> None:
        if self._phase_key is None or self._phase_t0 is None:
            return
        dt = max(0.0, time.perf_counter() - self._phase_t0)
        k = self._phase_key
        self._actual[k] = dt

        # EMA-обновление ожиданий (учимся на реальном времени)
        old = self._expected.get(k, dt if dt > 0 else 0.01)
        a = self.ema_alpha
        self._expected[k] = max(0.01, (1 - a) * old + a * dt)

        self._phase_key = None
        self._phase_t0 = None

        # сохраняем профиль по мере продвижения (чтобы даже краш дал пользу)
        self._save_cache()

    def _elapsed(self) -> float:
        return max(0.0, time.perf_counter() - self._t0)

    def _estimated_remaining(self) -> float:
        # остаток = сумма ожиданий фаз, которые ещё НЕ завершены
        rem = 0.0
        for k, _ in self.phases:
            if k not in self._actual:
                rem += self._expected.get(k, 0.01)
        # если мы сейчас внутри фазы — учитываем уже прошедшее внутри неё
        if self._phase_key and self._phase_t0:
            spent = max(0.0, time.perf_counter() - self._phase_t0)
            # но не даём уйти в отрицательные “остатки”
            rem = max(0.0, rem - spent)
        return rem

    def percent(self, *, allow_100: bool = False) -> float:
        elapsed = self._elapsed()
        rem = self._estimated_remaining()
        denom = max(0.001, elapsed + rem)
        p = 100.0 * (elapsed / denom)

        # ⚠️ 100% только когда реально готовы
        if not allow_100:
            p = min(p, 99.0)

        return _clamp(p, 0.0, 100.0)

    def update_loading(
        self,
        loading: "LoadingScreen",
        text: str = "Загрузка…",
        subtext: str | None = None,
        *,
        allow_100: bool = False,
    ) -> None:
        loading.update(self.percent(allow_100=allow_100), text=text, subtext=subtext)

    @contextmanager
    def phase(
        self,
        key: str,
        loading: "LoadingScreen",
        *,
        text: str = "Загрузка…",
        subtext: str | None = None,
    ):
        self.begin_phase(key)
        # ✅ сразу обновим, чтобы шкала не “дёргалась”
        self.update_loading(loading, text=text, subtext=subtext, allow_100=False)
        try:
            yield
        finally:
            self.end_phase()
            self.update_loading(loading, text=text, subtext=subtext, allow_100=False)

    def finish(self, loading: "LoadingScreen", text: str = "Готово", subtext: str | None = None) -> None:
        # ✅ 100% только здесь
        loading.update(100.0, text=text, subtext=subtext)

@dataclass
class LoadingScreen:
    """
    🧠 ЛОГИКА:
    Отдельное минимальное окно для загрузки (используем в engine_main.py до импортов).
    Потом закрываем и отдаём управление основному UI.
    """
    title: str = "DragonEngine"
    size: tuple[int, int] | None = None  # 🔧 МОЖНО МЕНЯТЬ: None = размер рабочего стола
    borderless: bool = True 
    resizable: bool = True             # 🔧 МОЖНО МЕНЯТЬ: True = без рамки (быстрее/чище)

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
        else:
            if self.resizable:
                flags |= pygame.RESIZABLE

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

@dataclass
class BootProgressPlan:
    """
    🧠 ЛОГИКА:
    План загрузки по фазам с оценками длительности (сек).
    Проценты — функция времени (perf_counter), почти линейно по ощущениям.
    """
    # 🔧 МОЖНО МЕНЯТЬ: оценки времени фаз (в секундах)
    est_imports_s: float = 0.55
    est_settings_s: float = 0.18
    est_editor_import_s: float = 0.45
    est_before_editor_s: float = 0.15

    def total_s(self) -> float:
        return max(
            0.05,
            float(self.est_imports_s + self.est_settings_s + self.est_editor_import_s + self.est_before_editor_s),
        )


class BootProgress:
    """
    🧠 ЛОГИКА:
    Обвязка над LoadingScreen, которая считает % по времени:
    percent = elapsed / total_est * 100

    Важно:
    - мы не пытаемся "обновлять во время import" (Python не даст),
      но как только фаза закончилась — % перескакивает ровно на то,
      сколько реально времени прошло.
    - 100% выставляем ТОЛЬКО в момент, когда реально готовы сразу звать run_editor().
    """
    def __init__(
        self,
        loader: "LoadingScreen",
        *,
        plan: BootProgressPlan | None = None,
        title: str = "Загрузка…",
        now: Callable[[], float] = time.perf_counter,
    ) -> None:
        self.loader = loader
        self.plan = plan or BootProgressPlan()
        self.title = title
        self._now = now
        self._t0 = self._now()

        # базовый текст
        self._last_text = title
        self._last_sub = "Инициализация"
        self.ping(self._last_sub, floor_pct=1.0)

    def _pct(self) -> float:
        elapsed = max(0.0, self._now() - self._t0)
        total = self.plan.total_s()
        pct = (elapsed / total) * 100.0
        # держим в [1..99] до финального commit в done()
        return float(max(1.0, min(99.0, pct)))

    def ping(self, subtext: str, *, floor_pct: float | None = None) -> None:
        pct = self._pct()
        if floor_pct is not None:
            pct = max(float(floor_pct), pct)
        self._last_sub = subtext
        self.loader.update(pct, self.title, subtext)

    def done(self, subtext: str = "Готово") -> None:
        # 100% ставим только когда реально сразу передаём управление UI
        self.loader.update(100, self.title, subtext)


    def close(self) -> None:
        """
        🧠 ЛОГИКА:
        Не убиваем pygame/display, чтобы не было "дёрганого" перехода:
        splash остаётся последним кадром, а основной UI перерисует то же окно.
        """
        return