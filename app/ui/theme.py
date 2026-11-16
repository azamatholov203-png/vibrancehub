"""Тема оформления в стиле macOS (тёмная)."""
from __future__ import annotations

QSS = """
* {
  font-family: 'SF Pro Display', 'SF Pro Text', 'Segoe UI Variable Display',
               'Segoe UI Variable', 'Segoe UI', 'Inter', sans-serif;
  font-size: 13px;
  color: #e9e9ec;
  selection-background-color: #0a84ff;
  selection-color: #ffffff;
}
QFrame#Root { background: #1f2026; border-radius: 12px; }
QFrame#Sidebar { background: #282a31; border-right: 1px solid #32343c; }

QLabel#AppTitle { color: #9a9aa3; font-size: 12px; font-weight: 700; letter-spacing: 2px; }
QLabel#Version  { color: #6f6f78; font-size: 11px; }
QLabel#PageTitle { font-size: 20px; font-weight: 700; color: #f4f4f6; }
QLabel#Subtitle  { color: #9c9ca4; font-size: 12px; }
QLabel#CardTitle { font-size: 13px; font-weight: 600; color: #f4f4f6; }
QLabel#Muted  { color: #9c9ca4; font-size: 12px; }
QLabel#Hint   { color: #8d8d96; font-size: 12px; }
QLabel#ValueLabel { font-weight: 600; }
QLabel#StatusPill { background: #33353d; border-radius: 11px; padding: 4px 12px;
                    color: #c9c9d1; font-size: 12px; }
QLabel#Toast { background: rgba(44, 46, 54, 95%); border-radius: 11px;
               padding: 8px 16px; color: #ffffff; font-size: 12px; }

QFrame#Card { background: #2a2c33; border-radius: 12px; }
QFrame#AdvFrame { background: #23252c; border-radius: 10px; }

QListWidget#Nav, QListWidget#PresetList {
  background: transparent; border: none; outline: none;
}
QListWidget#Nav::item { padding: 9px 12px; margin: 2px 6px; border-radius: 8px; color: #c9c9d1; }
QListWidget#Nav::item:hover { background: #32343c; }
QListWidget#Nav::item:selected { background: #0a84ff; color: #ffffff; }
QListWidget#PresetList::item { padding: 6px 8px; margin: 1px 4px; border-radius: 8px; }
QListWidget#PresetList::item:hover { background: #32343c; }
QListWidget#PresetList::item:selected { background: #3d3f4a; color: #ffffff; }

QLineEdit, QComboBox, QAbstractSpinBox {
  background: #23252c; border: 1px solid #3a3c45; border-radius: 8px;
  padding: 6px 10px; min-height: 18px; color: #e9e9ec;
}
QLineEdit:focus { border-color: #0a84ff; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow {
  image: url('__ARROW__');
  width: 11px; height: 11px; margin-right: 9px;
}
QComboBox QAbstractItemView {
  background: #2a2c33; border: 1px solid #3a3c45; border-radius: 8px;
  padding: 4px; outline: none; selection-background-color: #0a84ff;
}

QPushButton { background: #363841; border: none; border-radius: 8px;
              padding: 7px 14px; color: #e9e9ec; }
QPushButton:hover { background: #3f414b; }
QPushButton:pressed { background: #2f313a; }
QPushButton:disabled { background: #2c2e36; color: #77777f; }
QPushButton#Primary { background: #0a84ff; color: #ffffff; font-weight: 600; }
QPushButton#Primary:hover { background: #2b93ff; }
QPushButton#Primary:pressed { background: #0a74e0; }
QPushButton#Danger { background: #ff453a; color: #ffffff; font-weight: 600; }
QPushButton#Danger:hover { background: #ff6b62; }
QPushButton#Danger:disabled { background: #3a2a2a; color: #8a6f6d; }
QPushButton#Chip { background: #2e3038; border: 1px solid #3a3c45; border-radius: 14px;
                   padding: 5px 12px; color: #c9c9d1; font-size: 12px; }
QPushButton#Chip:hover { background: #3a3c45; color: #ffffff; }

QToolButton { background: transparent; border: none; color: #c9c9d1; padding: 3px; }
QToolButton:hover { color: #ffffff; }
QToolButton#TLClose { background: #ff5f57; border-radius: 6px;
  min-width: 13px; max-width: 13px; min-height: 13px; max-height: 13px; }
QToolButton#TLClose:hover { background: #ff837d; }
QToolButton#TLMin { background: #febc2e; border-radius: 6px;
  min-width: 13px; max-width: 13px; min-height: 13px; max-height: 13px; }
QToolButton#TLMin:hover { background: #ffcd57; }
QToolButton#TLZoom { background: #28c840; border-radius: 6px;
  min-width: 13px; max-width: 13px; min-height: 13px; max-height: 13px; }
QToolButton#TLZoom:hover { background: #4ed75f; }
QToolButton#AdvBtn { text-align: left; font-weight: 600; color: #c9c9d1; padding: 2px 0; }
QToolButton#AdvBtn:hover { color: #ffffff; }
QToolButton#RowDel { color: #ff8a81; font-weight: 700; border-radius: 6px; padding: 2px 8px; }
QToolButton#RowDel:hover { background: #3a3c45; }

QSlider::groove:horizontal { height: 4px; background: #3d3f48; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #0a84ff; border-radius: 2px; }
QSlider::handle:horizontal { width: 18px; height: 18px; margin: -8px 0;
  border-radius: 9px; background: #ffffff; border: 1px solid #a9a9b0; }
QSlider::handle:horizontal:hover { background: #f2f2f2; }
QSlider::groove:horizontal:disabled { background: #2c2e36; }

QTableWidget { background: transparent; border: none;
  alternate-background-color: #262830; gridline-color: transparent; outline: none; }
QTableWidget::item { padding: 6px; border: none; }
QTableWidget::item:selected { background: #0a84ff; color: #ffffff; }
QHeaderView { background: transparent; }
QHeaderView::section { background: #2a2c33; color: #9c9ca4; border: none;
  padding: 6px 8px; font-size: 12px; font-weight: 600; text-align: left; }
QTableCornerButton::section { background: #2a2c33; border: none; }

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QStackedWidget > QWidget { background: transparent; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #3d3f48; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #4a4c56; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #3d3f48; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

QMenu { background: #2a2c33; border: 1px solid #3a3c45; border-radius: 10px; padding: 6px; }
QMenu::item { padding: 6px 28px 6px 14px; border-radius: 6px; }
QMenu::item:selected { background: #0a84ff; color: #ffffff; }
QMenu::separator { height: 1px; background: #3a3c45; margin: 4px 8px; }

QToolTip { background: #2a2c33; color: #e9e9ec; border: 1px solid #3a3c45;
  padding: 5px 9px; border-radius: 6px; font-size: 12px; }

QMessageBox { background: #262830; }
QMessageBox QLabel { color: #e9e9ec; }
"""


def apply_theme(app) -> None:
    from ..core.config import resource_path
    arrow = resource_path('assets/arrow.png')
    qss = QSS.replace('__ARROW__', arrow.as_posix())
    app.setStyleSheet(qss)
