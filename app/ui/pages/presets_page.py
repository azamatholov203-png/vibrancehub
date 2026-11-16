"""Страница «Пресеты»: список слева, редактор справа (стиль macOS System Settings)."""
from __future__ import annotations

import uuid
from dataclasses import replace

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QScrollArea, QToolButton,
                               QVBoxLayout, QWidget)

from ...core.config import CATEGORIES, CAT_COLORS, Preset
from ..widgets import Card, PreviewBar, SliderRow


class PresetsPage(QWidget):
    def __init__(self, cfg, applier, main) -> None:
        super().__init__()
        self.cfg = cfg
        self.applier = applier
        self.main = main
        self._cur: Preset | None = None
        self._loading = False
        self._ids: list[str] = []

        h = QHBoxLayout(self)
        h.setContentsMargins(0, 4, 0, 0)
        h.setSpacing(16)

        # ---------------- left: list ----------------
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(10)
        self.list = QListWidget()
        self.list.setObjectName('PresetList')
        self.list.setFixedWidth(240)
        self.list.setIconSize(QSize(1, 1))
        self.list.currentRowChanged.connect(self._on_select)
        lv.addWidget(self.list, 1)
        btn_new = QPushButton('+ Новый пресет')
        btn_new.setObjectName('Primary')
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.clicked.connect(self._new)
        lv.addWidget(btn_new)
        lv.addWidget(self._hint_label(
            'Встроенные пресеты защищены от удаления, но их можно менять.'))
        h.addWidget(left)

        # ---------------- right: editor ----------------
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(12)
        card = Card('')
        rv.addWidget(card, 1)

        name_row = QHBoxLayout()
        name_row.setSpacing(10)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText('Название пресета')
        self.name_edit.textEdited.connect(self._on_name_edited)
        self.name_edit.editingFinished.connect(self._on_name_done)
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(CATEGORIES)
        self.cat_combo.setFixedWidth(150)
        self.cat_combo.currentIndexChanged.connect(self._on_category)
        name_row.addWidget(self.name_edit, 1)
        name_row.addWidget(self.cat_combo)
        card.add_layout(name_row)

        self.preview = PreviewBar(64)
        card.add(self.preview)

        self.vib = SliderRow('Насыщенность', 0, 100, 50, lambda v: f'{v} %',
                             'То же, что Digital Vibrance в NVIDIA Control Panel. '
                             '50 % — стандарт системы.')
        self.g = SliderRow('Гамма', 50, 200, 100, lambda v: f'{v / 100:.2f}',
                           'Больше 1.00 — светлее тени (видно врагов в тёмноте).')
        self.b = SliderRow('Яркость', -100, 100, 0, lambda v: f'{v:+d}',
                           'Общая яркость изображения.')
        self.c = SliderRow('Контраст', 50, 150, 100, lambda v: f'{v} %',
                           'Разница между светлыми и тёмными участками.')
        self.w = SliderRow('Теплота', -100, 100, 0, lambda v: f'{v:+d}',
                           'Плюс — теплее (краснее), минус — холоднее (синее).')
        card.add(self.vib)

        self.adv_btn = QToolButton()
        self.adv_btn.setObjectName('AdvBtn')
        self.adv_btn.setText('▸  Дополнительные фильтры')
        self.adv_btn.setToolTip('Гамма, яркость, контраст, теплота')
        self.adv_btn.setCheckable(True)
        self.adv_btn.setCursor(Qt.PointingHandCursor)
        card.add(self.adv_btn)

        adv = QFrame()
        adv.setObjectName('AdvFrame')
        av = QVBoxLayout(adv)
        av.setContentsMargins(12, 10, 12, 10)
        av.setSpacing(8)
        for row in (self.g, self.b, self.c, self.w):
            av.addWidget(row)
        adv.setVisible(False)
        self.adv_frame = adv
        card.add(adv)
        self.adv_btn.toggled.connect(self._toggle_adv)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        self.btn_apply = QPushButton('Применить')
        self.btn_apply.setObjectName('Primary')
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_dup = QPushButton('Дублировать')
        self.btn_del = QPushButton('Удалить')
        self.btn_del.setObjectName('Danger')
        for b in (self.btn_apply, self.btn_dup, self.btn_del):
            b.setCursor(Qt.PointingHandCursor)
        btns.addWidget(self.btn_apply)
        btns.addWidget(self.btn_dup)
        btns.addWidget(self.btn_del)
        btns.addStretch(1)
        card.add_layout(btns)

        self.slot_hint = self._hint_label('')
        card.add(self.slot_hint)

        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sc.setWidget(right)
        h.addWidget(sc, 1)

        self.btn_apply.clicked.connect(self._apply)
        self.btn_dup.clicked.connect(self._dup)
        self.btn_del.clicked.connect(self._del)
        for row in (self.vib, self.g, self.b, self.c, self.w):
            row.valueChanged.connect(self._write)
            row.released.connect(self._save)

        self.rebuild()

    @staticmethod
    def _hint_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName('Hint')
        lbl.setWordWrap(True)
        return lbl

    # ---------------- list ----------------
    def rebuild(self, select_id: str | None = None) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        self._ids = []
        for pr in self.cfg.presets:
            self._ids.append(pr.id)
            item = QListWidgetItem('')
            item.setSizeHint(QSize(0, 40))
            self.list.addItem(item)
            w = QWidget()
            wh = QHBoxLayout(w)
            wh.setContentsMargins(10, 4, 6, 4)
            wh.setSpacing(8)
            dot = QLabel()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(
                f"background: {CAT_COLORS.get(pr.category, '#ff375f')}; border-radius: 5px;")
            wh.addWidget(dot)
            nm = QLabel(pr.name)
            nm.setStyleSheet('font-size: 12.5px;')
            wh.addWidget(nm, 1)
            self.list.setItemWidget(item, w)
        idx = 0
        if select_id and select_id in self._ids:
            idx = self._ids.index(select_id)
        self.list.setCurrentRow(idx)
        self.list.blockSignals(False)
        self._on_select(idx)

    def select_by_id(self, pid: str) -> None:
        if pid in self._ids:
            self.list.setCurrentRow(self._ids.index(pid))

    def _on_select(self, row: int) -> None:
        pid = self._ids[row] if 0 <= row < len(self._ids) else None
        pr = self.cfg.preset_by_id(pid)
        self._loading = True
        self._cur = pr
        if pr is None:
            return
        self.name_edit.setText(pr.name)
        self.cat_combo.blockSignals(True)
        self.cat_combo.setCurrentText(pr.category)
        self.cat_combo.blockSignals(False)
        self.vib.set_value(pr.vibrance)
        self.g.set_value(round(pr.gamma * 100))
        self.b.set_value(pr.brightness)
        self.c.set_value(pr.contrast)
        self.w.set_value(pr.warmth)
        self.preview.set_params(vibrance=pr.vibrance, gamma=pr.gamma,
                                brightness=pr.brightness, contrast=pr.contrast,
                                warmth=pr.warmth)
        self.btn_del.setEnabled(not pr.builtin)
        slot = self._ids.index(pr.id) + 1
        self.slot_hint.setText(
            f'Глобальный хоткей: Ctrl+Alt+{slot}' if slot <= 8
            else 'Хоткеи работают для первых 8 пресетов (Ctrl+Alt+1..8)')
        self._loading = False

    # ---------------- editor ----------------
    def _toggle_adv(self, on: bool) -> None:
        self.adv_btn.setText('▾  Дополнительные фильтры' if on
                             else '▸  Дополнительные фильтры')
        self.adv_frame.setVisible(on)

    def _write(self) -> None:
        if self._loading or self._cur is None:
            return
        p = self._cur
        p.vibrance = self.vib.value()
        p.gamma = self.g.value() / 100.0
        p.brightness = self.b.value()
        p.contrast = self.c.value()
        p.warmth = self.w.value()
        self.preview.set_params(vibrance=p.vibrance, gamma=p.gamma,
                                brightness=p.brightness, contrast=p.contrast,
                                warmth=p.warmth)

    def _save(self) -> None:
        if self._cur is not None:
            self.cfg.save()

    def _on_name_edited(self, text: str) -> None:
        if self._cur is not None:
            self._cur.name = text or 'Без названия'

    def _on_name_done(self) -> None:
        if self._cur is not None:
            self.cfg.save()
            self.rebuild(select_id=self._cur.id)

    def _on_category(self) -> None:
        if self._loading or self._cur is None:
            return
        self._cur.category = self.cat_combo.currentText()
        self.cfg.save()
        self.rebuild(select_id=self._cur.id)

    # ---------------- actions ----------------
    def _apply(self) -> None:
        if self._cur is not None:
            self.applier.apply_preset(self._cur, 'manual')

    def _new(self) -> None:
        pr = Preset(id=uuid.uuid4().hex[:8], name='Новый пресет',
                    category='Своё', vibrance=60)
        self.cfg.add_preset(pr)
        self.rebuild(select_id=pr.id)
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def _dup(self) -> None:
        if self._cur is None:
            return
        copy = replace(self._cur, id=uuid.uuid4().hex[:8],
                       name=f'{self._cur.name} (копия)', builtin=False)
        self.cfg.add_preset(copy)
        self.rebuild(select_id=copy.id)

    def _del(self) -> None:
        if self._cur is None or self._cur.builtin:
            return
        pid = self._cur.id
        self.cfg.remove_preset(pid)
        self.rebuild(select_id=self.cfg.presets[0].id if self.cfg.presets else None)
        self.main.toast('Пресет удалён')
