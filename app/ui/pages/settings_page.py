"""Страница «Настройки»: автозапуск, хоткеи, гамма-разблокировка, сброс, о программе."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget)

from ...core.config import APP_NAME, APP_VERSION
from ...core.sysops import (autostart_enabled, gamma_unlocked, set_autostart,
                            set_gamma_unlock)
from ..widgets import Card, Switch


class SettingsPage(QWidget):
    def __init__(self, cfg, applier, main) -> None:
        super().__init__()
        self.cfg = cfg
        self.applier = applier
        self.main = main

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 4, 0, 0)
        v.setSpacing(14)

        # ---------------- general ----------------
        card1 = Card('Общие')
        self.sw_autostart = self._switch_row(card1, 'Автозапуск вместе с Windows',
                                             cfg.autostart, self._toggle_autostart)
        self.sw_min = self._switch_row(
            card1, 'Запускать свёрнутым в трей', cfg.start_minimized,
            lambda on: self._set('start_minimized', on))
        self.sw_notify = self._switch_row(
            card1, 'Показывать уведомление при смене пресета', cfg.notify,
            lambda on: self._set('notify', on))
        self.sw_apply = self._switch_row(
            card1, 'Применять пресет рабочего стола при старте', cfg.apply_on_start,
            lambda on: self._set('apply_on_start', on))
        self.sw_restore = self._switch_row(
            card1, 'Возвращать исходные настройки при выходе', cfg.restore_on_exit,
            lambda on: self._set('restore_on_exit', on))
        self.sw_hotkeys = self._switch_row(
            card1, 'Глобальные хоткеи (Ctrl+Alt+1..8 — пресеты, Ctrl+Alt+0 — рабочий стол)',
            cfg.hotkeys_enabled, self._toggle_hotkeys)
        v.addWidget(card1)

        # ---------------- gamma unlock ----------------
        card2 = Card('Полный диапазон гаммы')
        self.gamma_status = QLabel('')
        self.gamma_status.setObjectName('Muted')
        card2.add(self.gamma_status)
        card2.add_hint(
            'Windows по умолчанию ограничивает силу гамма-фильтров. Если яркость или '
            '«просветление теней» применяются слабо — сними ограничение. Потребуются '
            'права администратора (окно UAC). Изменяется ключ реестра '
            'HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\ICM.')
        row = QHBoxLayout()
        row.setSpacing(8)
        b_on = QPushButton('Разблокировать полный диапазон')
        b_on.setObjectName('Primary')
        b_on.setCursor(Qt.PointingHandCursor)
        b_on.clicked.connect(lambda: self._gamma_unlock(True))
        b_off = QPushButton('Вернуть как было')
        b_off.setCursor(Qt.PointingHandCursor)
        b_off.clicked.connect(lambda: self._gamma_unlock(False))
        row.addWidget(b_on)
        row.addWidget(b_off)
        row.addStretch(1)
        card2.add_layout(row)
        v.addWidget(card2)

        # ---------------- reset ----------------
        card3 = Card('Сброс')
        row2 = QHBoxLayout()
        row2.setSpacing(8)
        b_reset = QPushButton('Сбросить настройки и пресеты')
        b_reset.setObjectName('Danger')
        b_reset.setCursor(Qt.PointingHandCursor)
        b_reset.clicked.connect(self._reset)
        row2.addWidget(b_reset)
        row2.addStretch(1)
        card3.add_layout(row2)
        v.addWidget(card3)

        # ---------------- about ----------------
        card4 = Card(f'О программе ({APP_NAME} v{APP_VERSION})')
        about = QLabel(
            'Замена вкладки NVIDIA Control Panel: насыщенность через NVAPI '
            '(Digital Vibrance), системные фильтры через гамму Windows, пресеты, '
            'автопереключение по активной программе, хоткеи и трей. '
            'Работает даже если сама NVIDIA Control Panel не открывается.')
        about.setObjectName('Muted')
        about.setWordWrap(True)
        card4.add(about)
        v.addWidget(card4)

        v.addStretch(1)
        self.refresh()

    # ---------------- helpers ----------------
    def _switch_row(self, card: Card, text: str, checked: bool, cb) -> Switch:
        h = QHBoxLayout()
        h.setSpacing(10)
        sw = Switch()
        sw.set_checked(checked)
        lab = QLabel(text)
        lab.setWordWrap(True)
        h.addWidget(sw, 0, Qt.AlignTop)
        h.addWidget(lab, 1)
        card.add_layout(h)
        sw.toggled.connect(cb)
        return sw

    def _set(self, key: str, value) -> None:
        setattr(self.cfg, key, bool(value))
        self.cfg.save()

    def _toggle_autostart(self, on: bool) -> None:
        ok = set_autostart(bool(on))
        self.cfg.autostart = bool(on) and ok
        if not ok:
            self.sw_autostart.set_checked(False)
            self.main.toast('Не удалось изменить автозапуск (нужны обычные права пользователя)')
        self.cfg.save()

    def _toggle_hotkeys(self, on: bool) -> None:
        self.cfg.hotkeys_enabled = bool(on)
        self.cfg.save()
        if on:
            self.main._start_hotkeys()
        else:
            self.main._stop_hotkeys()

    def _gamma_unlock(self, on: bool) -> None:
        ok, msg = set_gamma_unlock(on)
        if ok:
            self.main.toast('Готово. Если фильтры всё ещё слабые — перезапусти приложение')
        else:
            self.main.toast(f'Не получилось: {msg}')
        self.refresh()

    def _reset(self) -> None:
        ret = QMessageBox.question(
            self, 'Сброс настроек',
            'Сбросить все пресеты, правила и настройки?\nИсходные значения монитора будут возвращены.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        self.applier.restore_original()
        self.cfg.reset_to_defaults()
        self.main.toast('Сброшено. Перезапусти VibranceHub, чтобы применить заново')

    def refresh(self) -> None:
        st = gamma_unlocked()
        if st is True:
            self.gamma_status.setText('Полный диапазон гаммы: разблокирован.')
        elif st is False:
            self.gamma_status.setText('Полный диапазон гаммы: стандартное ограничение Windows.')
        else:
            self.gamma_status.setText('Полный диапазон гаммы: состояние неизвестно.')
