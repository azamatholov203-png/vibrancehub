"""NVAPI (nvapi64.dll) — Digital Vibrance, тот же механизм, что у NVIDIA Control Panel.

Важно: nvapi64.dll экспортирует по имени ТОЛЬКО nvapi_QueryInterface — все
остальные функции получаются через неё по 32-битным ID интерфейсов. Метод
проверен годами (vibranceGUI, обёртка jNizM/AHK_NVIDIA_NvAPI — MIT):

  0x0150E828  NvAPI_Initialize              f()
  0xD22BDD7E  NvAPI_Unload                  f()
  0x9ABDD40D  NvAPI_EnumNVidiaDisplayHandle f(index, *handle)
  0x0E45002D  NvAPI_DVC_GetDVCLevelEx       f(hDisplay, outputId, *info20)
  0x4085DE45  NvAPI_DVC_GetStatusInfo       f(hDisplay, outputId, *info16)
  0x4A82C2B1  NvAPI_DVC_SetDVCLevelEx       f(hDisplay, outputId, *info20)
  0x172409B4  NvAPI_DVC_SetDVCLevel         f(hDisplay, outputId, level)
  0x6C2D048C  NvAPI_GetErrorMessage         f(status, *char64)

Структуры DVC: первый NvU32 — version = sizeof | 0x10000 (MAKE_NVAPI_VERSION);
далее Int: currentLevel, minLevel, maxLevel (Ex добавляет defaultLevel).
"""
from __future__ import annotations

import ctypes
import os
import struct
import sys


class NvApiError(Exception):
    pass


class NvDisplay:
    """Дисплей, найденный через NVAPI (handle + поддерживаемый диапазон DVC)."""

    __slots__ = ('handle', 'index', 'min_level', 'max_level', 'step')

    def __init__(self, handle: int, index: int, min_level: int, max_level: int, step: int):
        self.handle = handle
        self.index = index
        self.min_level = min_level
        self.max_level = max_level
        self.step = step

    def __repr__(self) -> str:  # pragma: no cover
        return f'NvDisplay(#{self.index}, levels {self.min_level}..{self.max_level})'


class BaseNvApi:
    name = 'base'
    available = False

    def displays(self) -> list[NvDisplay]:
        return []

    def get_level(self, d: NvDisplay) -> int:
        raise NotImplementedError

    def set_level(self, d: NvDisplay, level: int) -> None:
        raise NotImplementedError


class MockNvApi(BaseNvApi):
    """Для разработки/демо вне Windows: значения хранятся в памяти."""

    name = 'mock'
    available = True

    def __init__(self) -> None:
        self._levels = {0: 32}

    def displays(self) -> list[NvDisplay]:
        return [NvDisplay(1, 0, 0, 63, 1)]

    def get_level(self, d: NvDisplay) -> int:
        return self._levels.get(d.index, 32)

    def set_level(self, d: NvDisplay, level: int) -> None:
        self._levels[d.index] = int(max(0, min(d.max_level, level)))


class RealNvApi(BaseNvApi):
    name = 'nvapi'
    available = True

    ID_INITIALIZE = 0x0150E828
    ID_UNLOAD = 0xD22BDD7E
    ID_ENUM_DISPLAY = 0x9ABDD40D
    ID_GET_INFO_EX = 0x0E45002D
    ID_GET_INFO = 0x4085DE45
    ID_SET_LEVEL_EX = 0x4A82C2B1
    ID_SET_LEVEL = 0x172409B4
    ID_GET_ERROR = 0x6C2D048C

    INFO_EX_SIZE = 20   # version + current + min + max + default
    INFO_SIZE = 16      # version + current + min + max
    VER = 0x10000       # MAKE_NVAPI_VERSION(..., 1)

    def __init__(self) -> None:
        if sys.platform != 'win32':
            raise NvApiError('NVAPI доступен только на Windows')
        if 8 * struct.calcsize('P') != 64:
            raise NvApiError('Нужен 64-битный Python (32-битный не может загрузить nvapi64.dll)')
        try:
            self._dll = ctypes.WinDLL('nvapi64.dll')
        except OSError as e:
            raise NvApiError('nvapi64.dll не найдена — установлен ли драйвер NVIDIA?') from e

        self._dll.nvapi_QueryInterface.restype = ctypes.c_void_p
        self._dll.nvapi_QueryInterface.argtypes = [ctypes.c_uint]

        init = self._fn(self.ID_INITIALIZE, ctypes.c_int)
        rc = init()
        if rc != 0:
            raise NvApiError(f'NvAPI_Initialize вернула {self._err(rc)}')

        self._enum = self._fn(self.ID_ENUM_DISPLAY, ctypes.c_int,
                              ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p))
        self._get_ex = self._fn(self.ID_GET_INFO_EX, ctypes.c_int,
                                ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p)
        self._get = self._fn(self.ID_GET_INFO, ctypes.c_int,
                             ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p)
        self._set_ex = self._fn(self.ID_SET_LEVEL_EX, ctypes.c_int,
                                ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p)
        self._set = self._fn(self.ID_SET_LEVEL, ctypes.c_int,
                             ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint)
        self._get_err = self._fn(self.ID_GET_ERROR, ctypes.c_int,
                                 ctypes.c_uint, ctypes.c_char_p)

    # ---------------- helpers ----------------
    def _fn(self, iface_id: int, restype, *argtypes):
        """Функция NVAPI по ID интерфейса через nvapi_QueryInterface."""
        ptr = self._dll.nvapi_QueryInterface(iface_id)
        if not ptr:
            raise NvApiError(f'nvapi64.dll: интерфейс 0x{iface_id:08X} не найден '
                             '(драйвер NVIDIA слишком старый?)')
        proto = ctypes.WINFUNCTYPE(restype, *argtypes)
        return proto(ptr)

    def _err(self, status: int) -> str:
        status &= 0xFFFFFFFF
        try:
            buf = ctypes.create_string_buffer(64)
            self._get_err(status, buf)
            text = buf.value.decode('cp1251', errors='replace').strip()
            if text:
                return f'0x{status:08X} ({text})'
        except Exception:
            pass
        return f'0x{status:08X}'

    def _query_info(self, handle: int) -> tuple[int, int, int]:
        """(current, min, max) — через Ex-структуру, при неудаче через legacy."""
        h = ctypes.c_void_p(handle)
        for size, fn in ((self.INFO_EX_SIZE, self._get_ex), (self.INFO_SIZE, self._get)):
            buf = (ctypes.c_int * 6)()
            buf[0] = size | self.VER
            rc = fn(h, 0, ctypes.cast(buf, ctypes.c_void_p))
            if rc == 0:
                return int(buf[1]), int(buf[2]), int(buf[3])
            last_rc = rc
        raise NvApiError(f'DVC info: {self._err(last_rc)}')

    # ---------------- API ----------------
    def displays(self) -> list[NvDisplay]:
        res: list[NvDisplay] = []
        for i in range(64):
            h = ctypes.c_void_p()
            if self._enum(i, ctypes.byref(h)) != 0:
                break
            if not h.value:
                continue
            try:
                cur, mn, mx = self._query_info(h.value)
            except NvApiError:
                continue  # DVC не поддерживается этим дисплеем
            res.append(NvDisplay(h.value, i, mn, mx, 1))
        return res

    def get_level(self, d: NvDisplay) -> int:
        cur, _, _ = self._query_info(d.handle)
        return cur

    def set_level(self, d: NvDisplay, level: int) -> None:
        level = int(max(d.min_level, min(d.max_level, level)))
        h = ctypes.c_void_p(d.handle)
        buf = (ctypes.c_int * 6)()
        buf[0] = self.INFO_EX_SIZE | self.VER
        buf[1] = level
        rc = self._set_ex(h, 0, ctypes.cast(buf, ctypes.c_void_p))
        if rc != 0:
            rc = self._set(h, 0, level & 0xFFFFFFFF)
        if rc != 0:
            raise NvApiError(f'DVC set: {self._err(rc)}')


def create_backend() -> tuple[BaseNvApi | None, str | None]:
    """Возвращает (бэкенд, текст ошибки). Mock — только вне Windows или для теста."""
    if sys.platform != 'win32' or os.environ.get('VIBRANCEHUB_MOCK') == '1':
        return MockNvApi(), None
    try:
        return RealNvApi(), None
    except NvApiError as e:
        return None, str(e)
    except Exception as e:  # AttributeError и прочее — не роняем приложение
        return None, f'NVAPI: неожиданная ошибка: {e}'
