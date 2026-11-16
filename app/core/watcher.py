"""Фоновый слежатель активного окна (для автопереключения пресетов)."""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from . import procinfo


class Watcher(QThread):
    fg_changed = Signal(str)   # имя exe активного окна ('' — нет)

    def __init__(self, interval_ms: int = 1000) -> None:
        super().__init__()
        self._stop_evt = threading.Event()
        self.interval = max(0.3, interval_ms / 1000.0)
        self._last: object = object()   # сентинел, чтобы первое событие ушло сразу

    def set_interval(self, ms: int) -> None:
        self.interval = max(0.3, ms / 1000.0)

    def stop(self) -> None:
        self._stop_evt.set()

    def run(self) -> None:
        while not self._stop_evt.is_set():
            name = procinfo.get_foreground_process() or ''
            if name != self._last:
                self._last = name
                self.fg_changed.emit(name)
            self._stop_evt.wait(self.interval)
