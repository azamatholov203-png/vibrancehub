"""Страница «Автопереключение»: правила «программа -> пресет» и быстрые игры."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QToolButton, QVBoxLayout,
                               QWidget)

from ...core.config import CAT_COLORS
from ...core.procinfo import list_running_processes
from ..widgets import Card, Switch

# (название, имя процесса, категория пресета)
KNOWN_GAMES = [
    ('CS2', 'cs2.exe', 'Аркада'),
    ('Valorant', 'valorant-win64-shipping.exe', 'Аркада'),
    ('Apex Legends', 'r5apex.exe', 'Аркада'),
    ('Overwatch 2', 'overwatch.exe', 'Аркада'),
    ('PUBG', 'tslgame.exe', 'Аркада'),
    ('Fortnite', 'fortniteclient-win64-shipping.exe', 'Аркада'),
    ('Dota 2', 'dota2.exe', 'Аркада'),
    ('Escape from Tarkov', 'escapefromtarkov.exe', 'Война'),
    ('Squad', 'squadgame.exe', 'Война'),
    ('Hell Let Loose', 'hll-win64-shipping.exe', 'Война'),
    ('Rust', 'rustclient.exe', 'Война'),
    ('Call of Duty', 'cod.exe', 'Война'),
    ('Red Dead Redemption 2', 'rdr2.exe', 'Реализм'),
    ('GTA V', 'gta5.exe', 'Реализм'),
    ('Cyberpunk 2077', 'cyberpunk2077.exe', 'Реализм'),
    ('The Witcher 3', 'witcher3.exe', 'Реализм'),
]


class AutoshiftPage(QWidget):
    def __init__(self, cfg, applier, main) -> None:
        super().__init__()
        self.cfg = cfg
        self.applier = applier
        self.main = main

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 4, 0, 0)
        v.setSpacing(14)

        # ---------------- main card ----------------
        card1 = Card('Автопереключение')
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        self.switch = Switch()
        self.switch.set_checked(cfg.autoshift_enabled)
        self.switch.toggled.connect(self.main.on_autoshift_toggled)
        lab = QLabel('Следить за активным окном и менять пресет автоматически')
        row1.addWidget(self.switch)
        row1.addWidget(lab)
        row1.addStretch(1)
        card1.add_layout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        lab_desk = QLabel('Пресет для рабочего стола (когда игра не активна):')
        self.desk_combo = QComboBox()
        self.desk_combo.setMinimumWidth(150)
        row2.addWidget(lab_desk)
        row2.addWidget(self.desk_combo, 1)
        card1.add_layout(row2)
        self.desk_combo.currentIndexChanged.connect(self._on_desktop_changed)

        row3 = QHBoxLayout()
        row3.setSpacing(10)
        lab_int = QLabel('Интервал проверки:')
        self.interval = QComboBox()
        for ms in (500, 750, 1000, 1500, 2000, 3000, 5000):
            self.interval.addItem(f'{ms} мс', ms)
        idx = self.interval.findData(cfg.poll_interval_ms)
        self.interval.setCurrentIndex(max(0, idx))
        self.interval.setFixedWidth(120)
        self.interval.currentIndexChanged.connect(self._on_interval)
        row3.addWidget(lab_int)
        row3.addWidget(self.interval)
        row3.addStretch(1)
        card1.add_layout(row3)
        card1.add_hint(
            'Свернул игру — включается пресет рабочего стола, вернулся в игру — '
            'пресет игры. Изменение применяется мгновенно, даже в полноэкранном режиме.')
        v.addWidget(card1)

        # ---------------- rules ----------------
        card2 = Card('Правила: программа -> пресет')
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['Программа', 'Пресет', ''])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setColumnWidth(0, 330)
        self.table.setColumnWidth(1, 320)
        self.table.setColumnWidth(2, 56)
        self.table.setFixedHeight(210)
        card2.add(self.table)

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(8)
        self.proc_edit = QLineEdit()
        self.proc_edit.setPlaceholderText('имя процесса, напр. cs2.exe')
        self.proc_edit.setFixedWidth(250)
        self.proc_combo = QComboBox()
        self.proc_combo.setFixedWidth(250)
        self.proc_combo.setToolTip('Выбрать из запущенных процессов')
        btn_refresh = QPushButton('Обновить список')
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self._fill_running)
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(140)
        btn_add = QPushButton('Добавить правило')
        btn_add.setObjectName('Primary')
        btn_add.setCursor(Qt.PointingHandCursor)
        form.addWidget(self.proc_edit, 0, 0)
        form.addWidget(self.proc_combo, 0, 1)
        form.addWidget(btn_refresh, 0, 2)
        form.addWidget(self.preset_combo, 1, 0)
        form.addWidget(btn_add, 1, 1)
        card2.add_layout(form)
        card2.add_hint(
            'Имя процесса смотрят в Диспетчере задач (вкладка «Подробности», '
            'столбец «Имя образа») или выбирают из списка запущенных. '
            'Название можно писать без .exe — приложение допишет само.')
        v.addWidget(card2)

        # ---------------- known games ----------------
        card3 = Card('Популярные игры: добавить в один клик')
        rows: list[QHBoxLayout] = []
        current: QHBoxLayout | None = None
        for name, exe, cat in KNOWN_GAMES:
            if current is None or current.count() >= 4:
                current = QHBoxLayout()
                current.setSpacing(8)
                rows.append(current)
            chip = QPushButton(name)
            chip.setObjectName('Chip')
            chip.setCursor(Qt.PointingHandCursor)
            chip.setToolTip(f'{exe} -> пресет «{cat}»')
            chip.clicked.connect(
                lambda checked=False, e=exe, c=cat: self._add_known(e, c))
            current.addWidget(chip)
        for r in rows:
            r.addStretch(1)
            card3.add_layout(r)
        v.addWidget(card3)
        v.addStretch(1)

        btn_add.clicked.connect(self._add_rule)
        self.refresh()

    # ---------------- helpers ----------------
    def _fill_presets(self) -> None:
        self.desk_combo.blockSignals(True)
        self.preset_combo.blockSignals(True)
        self.desk_combo.clear()
        self.preset_combo.clear()
        for pr in self.cfg.presets:
            self.desk_combo.addItem(pr.name, pr.id)
            self.preset_combo.addItem(pr.name, pr.id)
        di = self.desk_combo.findData(self.cfg.desktop_preset)
        self.desk_combo.setCurrentIndex(max(0, di))
        self.desk_combo.blockSignals(False)
        self.preset_combo.blockSignals(False)

    def _fill_running(self) -> None:
        self.proc_combo.clear()
        self.proc_combo.addItem('— из запущенных —', None)
        for name in list_running_processes():
            self.proc_combo.addItem(name, name)
        self.proc_combo.setCurrentIndex(0)

    def _on_desktop_changed(self, idx: int) -> None:
        pid = self.desk_combo.itemData(idx)
        if pid:
            self.cfg.desktop_preset = pid
            self.cfg.save()

    def _on_interval(self, idx: int) -> None:
        val = self.interval.itemData(idx)
        if val:
            self.cfg.poll_interval_ms = int(val)
            if self.main.watcher is not None:
                self.main.watcher.set_interval(int(val))
            self.cfg.save()

    def _add_rule(self) -> None:
        name = self.proc_edit.text().strip() or (self.proc_combo.currentData() or '')
        pid = self.preset_combo.currentData()
        if not name or not pid:
            self.main.toast('Укажи программу и пресет')
            return
        if self.cfg.add_rule(name, pid):
            self.proc_edit.clear()
            self.rebuild()
            self.main.toast(f'Правило добавлено: {self.cfg.norm_process(name)}')
        else:
            self.main.toast('Такое правило уже существует')

    def _add_known(self, exe: str, cat: str) -> None:
        preset = next((pr for pr in self.cfg.presets if pr.category == cat), None)
        if preset is None:
            preset = self.cfg.preset_by_id(self.cfg.desktop_preset)
        if self.cfg.add_rule(exe, preset.id):
            self.rebuild()
            self.main.toast(f'Добавлено: {exe} -> «{preset.name}»')
        else:
            self.main.toast('Такое правило уже существует')

    def refresh(self) -> None:
        self._fill_presets()
        self._fill_running()
        self.rebuild()

    def rebuild(self) -> None:
        di = self.desk_combo.findData(self.cfg.desktop_preset)
        self.desk_combo.blockSignals(True)
        if di >= 0:
            self.desk_combo.setCurrentIndex(di)
        self.desk_combo.blockSignals(False)

        self.table.setRowCount(0)
        for i, rule in enumerate(self.cfg.rules):
            self.table.insertRow(i)
            pr = self.cfg.preset_by_id(rule['preset'])
            it1 = QTableWidgetItem(rule['process'])
            it1.setFlags(it1.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, it1)
            color = CAT_COLORS.get(pr.category, '#ff375f') if pr else '#ff375f'
            it2 = QTableWidgetItem(pr.name if pr else '(пресет удалён)')
            it2.setFlags(it2.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 1, it2)
            del_btn = QToolButton()
            del_btn.setObjectName('RowDel')
            del_btn.setText('Удалить')
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.clicked.connect(
                lambda checked=False, proc=rule['process']: self._del_rule(proc))
            self.table.setCellWidget(i, 2, del_btn)

    def _del_rule(self, proc: str) -> None:
        self.cfg.remove_rule(proc)
        self.rebuild()
        self.main.toast('Правило удалено')
