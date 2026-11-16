"""Применение пресетов к дисплею: насыщенность через NVAPI + фильтры через гамму."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .config import Config, Preset


class Applier(QObject):
    applied = Signal(object, str)   # (Preset | None, источник)
    failed = Signal(str)            # текст ошибки для тоста

    def __init__(self, nvapi, gamma, cfg: Config) -> None:
        super().__init__()
        self.nvapi = nvapi
        self.gamma = gamma
        self.cfg = cfg
        self.displays = []
        self.current: Preset | None = None
        self.current_vibrance: int | None = None
        self.current_source: str = ''
        self.original_levels: dict[int, int] = {}
        self.refresh_displays()

    # ---------------- displays ----------------
    def refresh_displays(self) -> None:
        self.displays = []
        if self.nvapi and self.nvapi.available:
            try:
                self.displays = self.nvapi.displays()
            except Exception as e:
                self.failed.emit(f'NVAPI: {e}')
        self.original_levels = {}
        for d in self.displays:
            try:
                self.original_levels[d.handle] = self.nvapi.get_level(d)
            except Exception:
                pass

    def _level_for(self, d, pct: int) -> int:
        mx = d.max_level or 63
        return max(0, min(mx, round(pct * mx / 100)))

    def _set_vibrance(self, pct: int) -> None:
        if not (self.nvapi and self.nvapi.available and self.displays):
            return
        for d in self.displays:
            self.nvapi.set_level(d, self._level_for(d, pct))

    # ---------------- presets ----------------
    def apply_preset(self, p: Preset, source: str = 'manual') -> None:
        ok = True
        try:
            self._set_vibrance(p.vibrance)
        except Exception as e:
            ok = False
            self.failed.emit(f'Насыщенность: {e}')
        if self.gamma and self.gamma.available:
            try:
                self.gamma.set_params(p.gamma, p.brightness, p.contrast, p.warmth)
            except Exception as e:
                ok = False
                self.failed.emit(str(e))
        if ok:
            self.current = p
            self.current_vibrance = p.vibrance
            self.current_source = source
            self.applied.emit(p, source)

    def apply_manual(self, vib: int) -> None:
        """Только насыщенность (страница «Монитор»), фильтры не трогаем."""
        try:
            self._set_vibrance(int(vib))
        except Exception as e:
            self.failed.emit(f'Насыщенность: {e}')
            return
        self.current = None
        self.current_vibrance = int(vib)
        self.current_source = 'manual'
        self.applied.emit(None, 'manual')

    def apply_filters(self, gamma: float, brightness: int, contrast: int, warmth: int) -> None:
        if self.gamma and self.gamma.available:
            try:
                self.gamma.set_params(gamma, brightness, contrast, warmth)
            except Exception as e:
                self.failed.emit(str(e))
                return
            self.current = None
            self.current_source = 'filters'
            self.applied.emit(None, 'filters')

    def reset_filters(self) -> None:
        if self.gamma and self.gamma.available:
            try:
                self.gamma.restore()
            except Exception as e:
                self.failed.emit(str(e))
                return
            self.current = None
            self.current_source = 'filters'
            self.applied.emit(None, 'filters')

    # ---------------- exit ----------------
    def restore_original(self) -> None:
        """Вернуть значения, которые были до запуска приложения."""
        if self.nvapi and self.nvapi.available and self.displays:
            try:
                for d in self.displays:
                    lvl = self.original_levels.get(d.handle)
                    if lvl is not None:
                        self.nvapi.set_level(d, lvl)
            except Exception:
                pass
        if self.gamma and self.gamma.available:
            try:
                self.gamma.restore()
            except Exception:
                pass
