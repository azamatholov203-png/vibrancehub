"""Системные фильтры: гамма / яркость / контраст / теплота через GDI (SetDeviceGammaRamp).

Работает на любой видеокарте (не только NVIDIA). Windows может отклонять
слишком сильные значения — в этом случае в Настройках можно снять ограничение
(ключ GdiIcmGammaRange).
"""
from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes


class GammaError(Exception):
    pass


def _channel_ramp(gamma: float, brightness: float, contrast: int) -> list[int]:
    """256 значений 0..65535 для одного канала."""
    out: list[int] = []
    c = contrast / 100.0
    b = brightness / 100.0 * 0.5          # -100..100 -> сдвиг -0.5..+0.5
    g = max(0.05, gamma)
    for i in range(256):
        t = i / 255.0
        t = (t - 0.5) * c + 0.5           # контраст вокруг середины
        t += b                             # яркость
        t = min(1.0, max(0.0, t))
        t = t ** (1.0 / g)                 # гамма (>1 светлее в тенях)
        out.append(int(round(t * 65535)))
    return out


def build_ramp(gamma: float, brightness: int, contrast: int, warmth: int) -> dict:
    """Три канала; теплота смещает красный и синий каналы в разные стороны."""
    w = max(-100, min(100, warmth)) / 100.0
    res = {}
    for name, sign in (('r', 1.0), ('g', 0.0), ('b', -1.0)):
        b = brightness + sign * w * 35.0
        g = gamma * (1.0 + 0.06 * sign * w)
        res[name] = _channel_ramp(g, b, contrast)
    return res


def is_neutral(gamma: float, brightness: int, contrast: int, warmth: int) -> bool:
    return (abs(gamma - 1.0) < 1e-9 and brightness == 0
            and contrast == 100 and warmth == 0)


class BaseGammaCtrl:
    available = False
    name = 'base'

    def __init__(self) -> None:
        self.params: tuple[float, int, int, int] = (1.0, 0, 100, 0)
        self.original: list[int] | None = None

    def get_params(self) -> tuple[float, int, int, int]:
        return self.params

    def set_params(self, gamma: float, brightness: int, contrast: int, warmth: int) -> None:
        raise NotImplementedError

    def restore(self) -> None:
        raise NotImplementedError


class MockGammaCtrl(BaseGammaCtrl):
    """Демо/тест вне Windows: хранит параметры в памяти."""

    available = True
    name = 'mock'

    def __init__(self) -> None:
        super().__init__()
        self.original = [min(65535, i * 257) for i in range(256)] * 3

    def set_params(self, gamma: float, brightness: int, contrast: int, warmth: int) -> None:
        if is_neutral(gamma, brightness, contrast, warmth):
            self.restore()
            return
        self.params = (float(gamma), int(brightness), int(contrast), int(warmth))

    def restore(self) -> None:
        self.params = (1.0, 0, 100, 0)


class RealGammaCtrl(BaseGammaCtrl):
    available = True
    name = 'gdi'

    def __init__(self) -> None:
        super().__init__()
        if sys.platform != 'win32':
            raise GammaError('Доступно только на Windows')
        self._u32 = ctypes.WinDLL('user32')
        self._g32 = ctypes.WinDLL('gdi32')
        self._u32.GetDC.restype = wintypes.HDC
        self._u32.GetDC.argtypes = [wintypes.HWND]
        self._hdc = self._u32.GetDC(None)
        if not self._hdc:
            raise GammaError('Не удалось получить контекст экрана')
        self._ramp_t = wintypes.WORD * (256 * 3)
        self._g32.GetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.POINTER(self._ramp_t)]
        self._g32.SetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.POINTER(self._ramp_t)]
        self.original = self._read()
        if self.original is None:
            ident = [min(65535, i * 257) for i in range(256)] * 3
            self.original = ident

    def _read(self) -> list[int] | None:
        buf = self._ramp_t()
        if self._g32.GetDeviceGammaRamp(self._hdc, buf):
            return list(buf)
        return None

    def _push(self, flat: list[int]) -> None:
        buf = self._ramp_t()
        for i, v in enumerate(flat):
            buf[i] = v & 0xFFFF
        if not self._g32.SetDeviceGammaRamp(self._hdc, buf):
            raise GammaError(
                'Windows отклонила гамму-рампу (слишком сильные значения). '
                'Помогает разблокировка полного диапазона в Настройках.')

    def set_params(self, gamma: float, brightness: int, contrast: int, warmth: int) -> None:
        if is_neutral(gamma, brightness, contrast, warmth):
            self.restore()
            return
        ch = build_ramp(gamma, brightness, contrast, warmth)
        self._push(ch['r'] + ch['g'] + ch['b'])
        self.params = (float(gamma), int(brightness), int(contrast), int(warmth))

    def restore(self) -> None:
        if self.original is not None:
            try:
                self._push(self.original)
            except GammaError:
                pass
        self.params = (1.0, 0, 100, 0)

    def close(self) -> None:
        try:
            self._u32.ReleaseDC(None, self._hdc)
        except Exception:
            pass


def create_gamma_ctrl() -> tuple[BaseGammaCtrl | None, str | None]:
    if sys.platform != 'win32' or os.environ.get('VIBRANCEHUB_MOCK') == '1':
        return MockGammaCtrl(), None
    try:
        return RealGammaCtrl(), None
    except Exception as e:
        return None, str(e)
