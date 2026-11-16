"""Значок в системном трее с меню пресетов."""
from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QIcon, QLinearGradient, QPainter,
                           QPixmap)
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .core.config import Config, resource_path


def app_icon() -> QIcon:
    """Иконка приложения: assets/icon.png или нарисованная на месте."""
    p = resource_path('assets/icon.png')
    if p.exists():
        return QIcon(str(p))
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    pt = QPainter(pm)
    pt.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 64, 64)
    grad.setColorAt(0, QColor('#0a84ff'))
    grad.setColorAt(1, QColor('#bf5af2'))
    pt.setBrush(QBrush(grad))
    pt.setPen(Qt.NoPen)
    pt.drawRoundedRect(4, 4, 56, 56, 14, 14)
    f = pt.font()
    f.setBold(True)
    f.setPixelSize(34)
    pt.setFont(f)
    pt.setPen(QColor('white'))
    pt.drawText(pm.rect(), Qt.AlignCenter, 'V')
    pt.end()
    return QIcon(pm)


class TrayMenu(QObject):
    open_requested = Signal()
    quit_requested = Signal()
    preset_selected = Signal(str)
    autoshift_toggled = Signal(bool)

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.cfg = cfg
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(app_icon())
        self.tray.setToolTip('VibranceHub')
        self.menu = QMenu()
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_activated)

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.open_requested.emit()

    def rebuild(self, cfg: Config, current_id: str | None) -> None:
        self.cfg = cfg
        self.menu.clear()
        for pr in cfg.presets:
            mark = '●  ' if pr.id == current_id else '    '
            self.menu.addAction(
                mark + pr.name,
                lambda checked=False, pid=pr.id: self.preset_selected.emit(pid))
        self.menu.addSeparator()
        act_auto = self.menu.addAction('Автопереключение')
        act_auto.setCheckable(True)
        act_auto.setChecked(cfg.autoshift_enabled)
        act_auto.triggered.connect(
            lambda checked: self.autoshift_toggled.emit(bool(checked)))
        self.menu.addSeparator()
        self.menu.addAction('Открыть VibranceHub', self.open_requested.emit)
        self.menu.addAction('Выход (вернуть настройки)', self.quit_requested.emit)

    def notify(self, title: str, body: str) -> None:
        if self.cfg.notify:
            self.tray.showMessage(title, body, QSystemTrayIcon.Information, 1800)

    def show(self) -> None:
        self.tray.show()

    def hide(self) -> None:
        self.tray.hide()
