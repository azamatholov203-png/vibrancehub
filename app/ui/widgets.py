"""Переиспользуемые виджеты в стиле macOS: свитч, слайдер-строка, карточка, превью."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (QAbstractButton, QFrame, QHBoxLayout, QLabel,
                               QSlider, QVBoxLayout, QWidget)


class Switch(QAbstractButton):
    """Свитч в стиле macOS (зелёный, с анимацией)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(44, 26)
        self.setCursor(Qt.PointingHandCursor)
        self._pos = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(130)
        self._anim.valueChanged.connect(self._on_anim)

    def _on_anim(self, v) -> None:
        self._pos = float(v)
        self.update()

    def set_checked(self, on: bool) -> None:
        self.setChecked(bool(on))
        self._pos = 1.0 if on else 0.0
        self.update()

    def nextCheckState(self) -> None:
        super().nextCheckState()
        self._animate()

    def _animate(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if self.isChecked() else 0.0)
        self._anim.start()

    def paintEvent(self, e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        track = QColor('#30d158') if self.isChecked() else QColor('#48484e')
        if not self.isEnabled():
            track = QColor('#3a3a40')
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, 44, 26), 13, 13)
        x = 3.0 + self._pos * 18.0
        p.setBrush(QColor('#ffffff'))
        p.drawEllipse(QRectF(x, 3, 20, 20))


class SliderRow(QWidget):
    """Строка «подпись — слайдер — значение». Сигнал released — применить на отпускание."""
    valueChanged = Signal(int)
    released = Signal()

    def __init__(self, text: str, lo: int, hi: int, value: int,
                 fmt=None, note: str = '', label_width: int = 150) -> None:
        super().__init__()
        self._fmt = fmt or (lambda v: str(v))
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        lab = QLabel(text)
        lab.setMinimumWidth(label_width)
        h.addWidget(lab)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(lo, hi)
        self.slider.setValue(int(value))
        self.slider.setCursor(Qt.PointingHandCursor)
        h.addWidget(self.slider, 1)
        self.value_label = QLabel(self._fmt(int(value)))
        self.value_label.setObjectName('ValueLabel')
        self.value_label.setMinimumWidth(64)
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(self.value_label)
        self.slider.valueChanged.connect(self._on_change)
        self.slider.sliderReleased.connect(self.released)
        if note:
            self.setToolTip(note)

    def _on_change(self, v: int) -> None:
        self.value_label.setText(self._fmt(v))
        self.valueChanged.emit(v)

    def set_value(self, v: int) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(int(v))
        self.slider.blockSignals(False)
        self.value_label.setText(self._fmt(int(v)))

    def value(self) -> int:
        return self.slider.value()


class Card(QFrame):
    def __init__(self, title: str = '') -> None:
        super().__init__()
        self.setObjectName('Card')
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 16)
        v.setSpacing(10)
        if title:
            t = QLabel(title)
            t.setObjectName('CardTitle')
            v.addWidget(t)
        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        v.addLayout(self.body)

    def add(self, w: QWidget) -> QWidget:
        self.body.addWidget(w)
        return w

    def add_layout(self, lay) -> None:
        self.body.addLayout(lay)

    def add_hint(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName('Hint')
        lbl.setWordWrap(True)
        self.body.addWidget(lbl)
        return lbl


class PreviewBar(QWidget):
    """Живое превью радуги с применёнными параметрами пресета."""
    def __init__(self, height: int = 64, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(height)
        self._p = dict(vibrance=50, gamma=1.0, brightness=0, contrast=100, warmth=0)

    def set_params(self, **kw) -> None:
        self._p.update(kw)
        self.update()

    def params(self) -> dict:
        return dict(self._p)

    def paintEvent(self, e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        p.setClipPath(path)
        w = max(2, self.width())
        vib = min(2.0, self._p['vibrance'] / 50.0)
        s0 = min(1.0, 0.75 * vib)
        c = self._p['contrast'] / 100.0
        b = self._p['brightness'] / 100.0 * 0.5
        g = max(0.05, float(self._p['gamma']))
        wr = self._p['warmth'] / 100.0
        for x in range(w):
            hue = x / (w - 1)
            s = s0
            v = 0.72
            v = (v - 0.5) * c + 0.5 + b
            v = min(1.0, max(0.0, v))
            v = v ** (1.0 / g)
            col = QColor.fromHsvF(hue, s, max(0.0, min(1.0, v)))
            if wr != 0.0:
                k = min(1.0, abs(wr) * 0.45)
                tint = QColor(255, 170, 90) if wr > 0 else QColor(110, 160, 255)
                col = QColor(
                    int(col.red() * (1 - k) + tint.red() * k),
                    int(col.green() * (1 - k) + tint.green() * k),
                    int(col.blue() * (1 - k) + tint.blue() * k),
                )
            p.setPen(col)
            p.drawLine(x, 0, x, self.height())
        p.end()


class StatusRow(QWidget):
    """Строка статуса с цветной точкой (для страницы «Монитор»)."""
    def __init__(self, color: str, text: str, wrap: bool = True) -> None:
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f'background: {color}; border-radius: 5px;')
        h.addWidget(dot, 0, Qt.AlignVCenter)
        lab = QLabel(text)
        lab.setWordWrap(wrap)
        lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        h.addWidget(lab, 1)
