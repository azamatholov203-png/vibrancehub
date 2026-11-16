"""Страница «Монитор»: дисплеи, ручная насыщенность и системные фильтры."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                               QWidget)

from ..widgets import Card, PreviewBar, SliderRow, StatusRow


class MonitorPage(QWidget):
    def __init__(self, cfg, applier, main, nv_err=None, g_err=None) -> None:
        super().__init__()
        self.cfg = cfg
        self.applier = applier
        self.main = main
        self.nv_err = nv_err
        self.g_err = g_err

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 4, 0, 0)
        v.setSpacing(14)

        # ---------------- displays ----------------
        card_disp = Card('Дисплеи и поддержка NVIDIA')
        self.disp_body = card_disp.body
        v.addWidget(card_disp)

        # ---------------- vibrance ----------------
        card_vib = Card('Насыщенность (Digital Vibrance)')
        self.vib = SliderRow('Насыщенность', 0, 100, 50, lambda val: f'{val} %',
                             'Применяется сразу при отпускании ползунка. '
                             '50 % — стандарт Windows.')
        card_vib.add(self.vib)
        self.vib_preview = PreviewBar(52)
        card_vib.add(self.vib_preview)
        row = QHBoxLayout()
        row.setSpacing(8)
        b50 = QPushButton('50 % (стандарт)')
        b100 = QPushButton('100 %')
        for b in (b50, b100):
            b.setCursor(Qt.PointingHandCursor)
        b50.clicked.connect(lambda: self._set_vib(50))
        b100.clicked.connect(lambda: self._set_vib(100))
        row.addWidget(b50)
        row.addWidget(b100)
        row.addStretch(1)
        card_vib.add_layout(row)
        card_vib.add_hint('Меняется только насыщенность, фильтры гаммы не трогаются. '
                          'Пресет «Монитор» работает в полноэкранных играх — '
                          'значение применяется на уровне драйвера.')
        v.addWidget(card_vib)

        # ---------------- filters ----------------
        card_f = Card('Системные фильтры (гамма / яркость / контраст / теплота)')
        self.g = SliderRow('Гамма', 50, 200, 100, lambda val: f'{val / 100:.2f}',
                           'Больше 1.00 — светлее тени. Это «black equalizer» для шутеров.')
        self.b = SliderRow('Яркость', -100, 100, 0, lambda val: f'{val:+d}')
        self.c = SliderRow('Контраст', 50, 150, 100, lambda val: f'{val} %')
        self.ww = SliderRow('Теплота', -100, 100, 0, lambda val: f'{val:+d}',
                            'Плюс — теплее (как Night Light), минус — холоднее.')
        for rowf in (self.g, self.b, self.c, self.ww):
            card_f.add(rowf)
            rowf.valueChanged.connect(self._update_preview)
        self.f_preview = PreviewBar(52)
        card_f.add(self.f_preview)
        btns = QHBoxLayout()
        btns.setSpacing(8)
        btn_apply_f = QPushButton('Применить фильтры')
        btn_apply_f.setObjectName('Primary')
        btn_apply_f.setCursor(Qt.PointingHandCursor)
        btn_apply_f.clicked.connect(self._apply_filters)
        btn_reset = QPushButton('Сбросить фильтры')
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.clicked.connect(self._reset_filters)
        btns.addWidget(btn_apply_f)
        btns.addWidget(btn_reset)
        btns.addStretch(1)
        card_f.add_layout(btns)
        self.f_status = QLabel('')
        self.f_status.setObjectName('Hint')
        self.f_status.setWordWrap(True)
        card_f.add(self.f_status)
        card_f.add_hint(
            'Фильтры применяются через системную гамму Windows (работают на любой '
            'видеокарте). Windows может отклонять слишком сильные значения — тогда '
            'сними ограничение кнопкой «Разблокировать полный диапазон» в Настройках. '
            'Если включен HDR — эффекты могут не отображаться.')
        v.addWidget(card_f)

        v.addStretch(1)
        self.refresh()

    # ---------------- helpers ----------------
    def _update_preview(self) -> None:
        self.vib_preview.set_params(
            vibrance=self.vib.value(),
            gamma=self.g.value() / 100, brightness=self.b.value(),
            contrast=self.c.value(), warmth=self.ww.value())
        self.f_preview.set_params(
            vibrance=self.vib.value(),
            gamma=self.g.value() / 100, brightness=self.b.value(),
            contrast=self.c.value(), warmth=self.ww.value())

    def _set_vib(self, val: int) -> None:
        self.vib.set_value(val)
        self.applier.apply_manual(val)
        self._update_preview()

    def _apply_filters(self) -> None:
        self.applier.apply_filters(
            self.g.value() / 100, self.b.value(), self.c.value(), self.ww.value())

    def _reset_filters(self) -> None:
        self.applier.reset_filters()

    def set_status(self, text: str) -> None:
        self.f_status.setText(text)

    def sync_from_applier(self) -> None:
        a = self.applier
        if a.current_vibrance is not None:
            self.vib.set_value(a.current_vibrance)
        if a.gamma and a.gamma.available:
            gp = a.gamma.get_params()
            self.g.set_value(round(gp[0] * 100))
            self.b.set_value(gp[1])
            self.c.set_value(gp[2])
            self.ww.set_value(gp[3])
        self._update_preview()

    def refresh(self) -> None:
        # очистка блока дисплеев
        while self.disp_body.count():
            it = self.disp_body.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()
        a = self.applier
        if a.nvapi is None or not getattr(a.nvapi, 'available', False):
            msg = self.nv_err or 'NVIDIA API недоступен'
            self.disp_body.addWidget(
                StatusRow('#ff453a',
                          f'Насыщенность через NVIDIA недоступна: {msg}. '
                          'Проверь драйвер NVIDIA и 64-битный Python. '
                          'Фильтры гаммы при этом работают.'))
        else:
            mock = getattr(a.nvapi, 'name', '') == 'mock'
            if mock:
                self.disp_body.addWidget(
                    StatusRow('#ff9f0a',
                              'Демо-режим: изменения никуда не применяются '
                              '(запущено без NVIDIA).'))
            if not a.displays:
                self.disp_body.addWidget(
                    StatusRow('#ff9f0a',
                              'NVIDIA не вернула дисплеев с поддержкой Digital Vibrance.'))
            for d in a.displays:
                self.disp_body.addWidget(
                    StatusRow('#30d158',
                              f'Дисплей #{d.index} — DVC поддерживается, '
                              f'уровни {d.min_level}–{d.max_level}, шаг {d.step}'))
        # текущие значения
        try:
            if a.nvapi and a.nvapi.available and a.displays:
                d0 = a.displays[0]
                lvl = a.nvapi.get_level(d0)
                self.vib.set_value(round(lvl * 100 / (d0.max_level or 63)))
        except Exception:
            pass
        self.sync_from_applier()
