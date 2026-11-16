"""Главное окно в стиле macOS: боковая панель, traffic lights, тосты, сервисы."""
from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QScrollArea,
                               QStackedWidget, QToolButton, QVBoxLayout,
                               QWidget)

from ..core.config import APP_VERSION, Config, Preset
from ..core.hotkeys import HotkeyManager
from ..core.procinfo import own_process_names
from ..core.watcher import Watcher
from ..tray import TrayMenu, app_icon
from .pages.autoshift_page import AutoshiftPage
from .pages.monitor_page import MonitorPage
from .pages.presets_page import PresetsPage
from .pages.settings_page import SettingsPage

SOURCE_LABELS = {
    'manual': 'вручную',
    'auto': 'авто',
    'auto-desktop': 'авто',
    'hotkey': 'хоткей',
    'tray': 'трей',
    'start': 'старт',
    'filters': 'фильтры',
}

PAGES = [
    ('Пресеты', 'Готовые профили цвета и свои пресеты'),
    ('Монитор', 'Ручная настройка насыщенности и фильтров дисплея'),
    ('Автопереключение', 'Смена пресета по активной программе'),
    ('Настройки', 'Поведение приложения и системные опции'),
]


class HotkeyBridge(QObject):
    trigger = Signal(int)


class TitleBar(QWidget):
    def __init__(self, win: 'MainWindow') -> None:
        super().__init__(win)
        self.setFixedHeight(46)
        self._drag = None
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 8, 14, 4)
        h.setSpacing(8)
        b_close = QToolButton()
        b_close.setObjectName('TLClose')
        b_min = QToolButton()
        b_min.setObjectName('TLMin')
        b_zoom = QToolButton()
        b_zoom.setObjectName('TLZoom')
        for b in (b_close, b_min, b_zoom):
            b.setCursor(Qt.PointingHandCursor)
        b_close.setToolTip('Свернуть в трей')
        b_min.setToolTip('Свернуть окно')
        b_zoom.setToolTip('Увеличить окно')
        b_close.clicked.connect(win.traffic_close)
        b_min.clicked.connect(win.showMinimized)
        b_zoom.clicked.connect(win.traffic_zoom)
        h.addWidget(b_close)
        h.addWidget(b_min)
        h.addWidget(b_zoom)
        h.addSpacing(6)
        t = QLabel('VibranceHub')
        t.setObjectName('AppTitle')
        h.addWidget(t)
        h.addStretch(1)
        self.pill = QLabel('Готово')
        self.pill.setObjectName('StatusPill')
        h.addWidget(self.pill)

    # перетаскивание окна за заголовок
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, e) -> None:
        if self._drag is not None and e.buttons() & Qt.LeftButton:
            self.window().move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e) -> None:
        self._drag = None

    def mouseDoubleClickEvent(self, e) -> None:
        self.window().traffic_zoom()


class MainWindow(QWidget):
    def __init__(self, cfg: Config, applier, nv_err: str | None = None,
                 g_err: str | None = None, start_services: bool = True) -> None:
        super().__init__()
        self.cfg = cfg
        self.applier = applier
        self.nv_err = nv_err
        self.g_err = g_err
        self._last_fg = ''
        self._zoomed = False
        self._old_geom = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(app_icon())
        self.setMinimumSize(960, 620)
        self.resize(1040, 690)
        self.setWindowTitle('VibranceHub')

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        root = QFrame()
        root.setObjectName('Root')
        outer.addWidget(root)

        v = QVBoxLayout(root)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.titlebar = TitleBar(self)
        v.addWidget(self.titlebar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        v.addLayout(body, 1)

        # ---------- sidebar ----------
        sidebar = QFrame()
        sidebar.setObjectName('Sidebar')
        sidebar.setFixedWidth(222)
        sv = QVBoxLayout(sidebar)
        sv.setContentsMargins(12, 8, 12, 14)
        sv.setSpacing(6)
        self.nav = QListWidget()
        self.nav.setObjectName('Nav')
        for name, _ in PAGES:
            self.nav.addItem(QListWidgetItem(name))
        sv.addWidget(self.nav)
        sv.addStretch(1)
        nv_ok = bool(self.applier.nvapi and self.applier.nvapi.available)
        nv_row = QHBoxLayout()
        nv_row.setSpacing(8)
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(
            f"background: {'#30d158' if nv_ok else '#ff453a'}; border-radius: 4px;")
        nv_lab = QLabel('NVIDIA: доступна' if nv_ok else 'NVIDIA: недоступна')
        nv_lab.setObjectName('Muted')
        nv_row.addWidget(dot)
        nv_row.addWidget(nv_lab)
        nv_row.addStretch(1)
        sv.addLayout(nv_row)
        ver = QLabel(f'v{APP_VERSION}')
        ver.setObjectName('Version')
        sv.addWidget(ver)
        body.addWidget(sidebar)

        # ---------- content ----------
        content = QWidget()
        cv = QVBoxLayout(content)
        cv.setContentsMargins(26, 6, 26, 16)
        cv.setSpacing(8)
        self.page_title = QLabel(PAGES[0][0])
        self.page_title.setObjectName('PageTitle')
        self.page_sub = QLabel(PAGES[0][1])
        self.page_sub.setObjectName('Subtitle')
        cv.addWidget(self.page_title)
        cv.addWidget(self.page_sub)
        self.stack = QStackedWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self.stack)
        cv.addWidget(scroll, 1)
        body.addWidget(content, 1)

        # ---------- pages ----------
        self.presets_page = PresetsPage(cfg, applier, self)
        self.monitor_page = MonitorPage(cfg, applier, self, nv_err, g_err)
        self.autoshift_page = AutoshiftPage(cfg, applier, self)
        self.settings_page = SettingsPage(cfg, applier, self)
        for pg in (self.presets_page, self.monitor_page,
                   self.autoshift_page, self.settings_page):
            self.stack.addWidget(pg)
        self.nav.currentRowChanged.connect(self._on_nav)
        self.nav.setCurrentRow(0)

        # ---------- tray ----------
        self.tray = TrayMenu(cfg)
        self.tray.preset_selected.connect(
            lambda pid: self._apply_by_id(pid, 'tray'))
        self.tray.open_requested.connect(self._show_from_tray)
        self.tray.quit_requested.connect(self.quit_app)
        self.tray.autoshift_toggled.connect(self.on_autoshift_toggled)
        self.tray.rebuild(cfg, None)
        self.tray.show()

        # ---------- services ----------
        self.watcher: Watcher | None = None
        self.hotkeys: HotkeyManager | None = None
        self.hotkey_bridge = HotkeyBridge()
        self.hotkey_bridge.trigger.connect(self.on_hotkey)
        if start_services:
            self.watcher = Watcher(cfg.poll_interval_ms)
            self.watcher.fg_changed.connect(self.on_fg_changed)
            self.watcher.start()
            if sys.platform == 'win32' and cfg.hotkeys_enabled:
                self._start_hotkeys()
        # драйвер NVIDIA сбрасывает насыщенность при смене видеорежима
        # (запуск/выход из полноэкранной игры) — периодически переприменяем
        self._reassert_timer = QTimer(self)
        self._reassert_timer.setInterval(5000)
        self._reassert_timer.timeout.connect(self._reassert_vibrance)
        if start_services:
            self._reassert_timer.start()
        if start_services and cfg.apply_on_start:
            QTimer.singleShot(500, self._apply_desktop)

        self.applier.applied.connect(self.on_applied)
        self.applier.failed.connect(self.on_failed)

    # ---------------- navigation ----------------
    def _on_nav(self, i: int) -> None:
        self.stack.setCurrentIndex(i)
        self.page_title.setText(PAGES[i][0])
        self.page_sub.setText(PAGES[i][1])
        if i == 1:
            self.monitor_page.refresh()
        elif i == 2:
            self.autoshift_page.refresh()
        elif i == 3:
            self.settings_page.refresh()

    def nav_set_page(self, i: int) -> None:
        self.nav.setCurrentRow(i)

    # ---------------- window controls ----------------
    def traffic_close(self) -> None:
        self.hide()
        self.toast('Свернуто в трей. Выход — правой кнопкой по значку в трее')

    def traffic_zoom(self) -> None:
        scr = self.screen().availableGeometry()
        if self._zoomed and self._old_geom is not None:
            self.setGeometry(self._old_geom)
            self._zoomed = False
            return
        self._old_geom = self.geometry()
        w = min(1260, scr.width() - 80)
        h = min(840, scr.height() - 80)
        self.setGeometry((scr.width() - w) // 2, (scr.height() - h) // 2, w, h)
        self._zoomed = True

    def closeEvent(self, e) -> None:
        e.ignore()
        self.traffic_close()

    # ---------------- applying ----------------
    def _apply_by_id(self, pid: str, source: str) -> None:
        p = self.cfg.preset_by_id(pid)
        if p:
            self.applier.apply_preset(p, source)

    def _apply_desktop(self) -> None:
        self._apply_by_id(self.cfg.desktop_preset, 'start')

    def on_applied(self, p: Preset | None, source: str) -> None:
        if p is not None:
            self._set_status_pill(f'{p.name}  ·  {SOURCE_LABELS.get(source, source)}')
            if source in ('auto', 'auto-desktop'):
                text = f'Пресет «{p.name}»'
                if source == 'auto':
                    text += f' — активна: {self._last_fg}'
                self.tray.notify('VibranceHub', text)
                self.toast(text)
        else:
            if source == 'filters':
                self._set_status_pill('фильтры изменены')
            else:
                self._set_status_pill(
                    f'{self.applier.current_vibrance} %  ·  '
                    f'{SOURCE_LABELS.get(source, source)}')
        self.tray.rebuild(self.cfg, p.id if p else None)
        self.monitor_page.sync_from_applier()

    def on_failed(self, text: str) -> None:
        self.toast('Ошибка: ' + text)
        self.monitor_page.set_status(text)

    def on_fg_changed(self, name: str) -> None:
        self._last_fg = name
        if not self.cfg.autoshift_enabled:
            return
        if not name or name in own_process_names():
            return
        rule = self.cfg.find_rule(name)
        if rule:
            # известная игра — всегда применяем её пресет
            target, source = rule['preset'], 'auto'
        else:
            # окно без правила: возвращаемся к пресету рабочего стола ТОЛЬКО
            # если сейчас активен авто-пресет игры (вышел из игры). Ручной
            # выбор пользователя не перебиваем.
            if self.applier.current_source != 'auto':
                return
            target, source = self.cfg.desktop_preset, 'auto-desktop'
        cur = self.applier.current.id if self.applier.current else None
        if cur == target and self.applier.current_source.startswith('auto'):
            return
        self._apply_by_id(target, source)

    def on_autoshift_toggled(self, on: bool) -> None:
        self.cfg.autoshift_enabled = bool(on)
        self.cfg.save()
        self.tray.rebuild(self.cfg, self.applier.current.id if self.applier.current else None)
        if not on:
            self._apply_by_id(self.cfg.desktop_preset, 'auto-desktop')
            self.toast('Автопереключение выключено — применён пресет рабочего стола')

    # ---------------- hotkeys ----------------
    def _start_hotkeys(self) -> None:
        if self.hotkeys is not None:
            return
        if sys.platform != 'win32':
            return
        self.hotkeys = HotkeyManager(self.hotkey_bridge.trigger.emit)
        self.hotkeys.start()

    def _stop_hotkeys(self) -> None:
        if self.hotkeys is not None:
            self.hotkeys.stop()
            self.hotkeys = None

    def on_hotkey(self, hid: int) -> None:
        if not self.cfg.hotkeys_enabled:
            return
        if hid == 0:
            self._apply_by_id(self.cfg.desktop_preset, 'hotkey')
            return
        idx = hid - 1
        if 0 <= idx < len(self.cfg.presets):
            self.applier.apply_preset(self.cfg.presets[idx], 'hotkey')

    # ---------------- misc ----------------
    def _reassert_vibrance(self) -> None:
        """Если фактический уровень насыщенности разошёлся с выбранным (драйвер
        сбросил его при смене видеорежима) — молча возвращаем значение."""
        a = self.applier
        if not (a.nvapi and a.nvapi.available and a.displays):
            return
        want = a.current_vibrance
        if want is None:
            return
        try:
            for d in a.displays:
                lvl = a._level_for(d, want)
                if a.nvapi.get_level(d) != lvl:
                    a.nvapi.set_level(d, lvl)
        except Exception:
            pass

    def _set_status_pill(self, text: str) -> None:
        self.titlebar.pill.setText(text)

    def toast(self, text: str, ms: int = 2600) -> None:
        if not hasattr(self, '_toast'):
            self._toast = QLabel(self)
            self._toast.setObjectName('Toast')
            self._toast.setAlignment(Qt.AlignCenter)
            self._toast_timer = QTimer(self)
            self._toast_timer.setSingleShot(True)
            self._toast_timer.timeout.connect(self._toast.hide)
        self._toast.setText(text)
        self._toast.adjustSize()
        w = min(self.width() - 40, max(240, self._toast.width()))
        self._toast.setGeometry((self.width() - w) // 2, 54, w, self._toast.height())
        self._toast.show()
        self._toast.raise_()
        self._toast_timer.start(ms)

    def _show_from_tray(self) -> None:
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def quit_app(self) -> None:
        self.cfg.save()
        self.applier.restore_original()
        if self.watcher is not None:
            self.watcher.stop()
        self._stop_hotkeys()
        self.tray.hide()
        QApplication.instance().quit()
