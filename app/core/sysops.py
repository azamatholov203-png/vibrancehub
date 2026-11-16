"""Системные операции: автозапуск с Windows и разблокировка полного диапазона гаммы."""
from __future__ import annotations

import ctypes
import os
import sys

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
VALUE_NAME = 'VibranceHub'
ICM_KEY = r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM'
GAMMA_VAL = 'GdiIcmGammaRange'


def _command() -> str:
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    py = sys.executable
    pyw = os.path.join(os.path.dirname(py), 'pythonw.exe')
    if os.path.exists(pyw):
        py = pyw
    return f'"{py}" "{os.path.abspath(sys.argv[0])}"'


def autostart_enabled() -> bool:
    if sys.platform != 'win32':
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            v, _ = winreg.QueryValueEx(k, VALUE_NAME)
            return bool(v)
    except OSError:
        return False


def set_autostart(on: bool) -> bool:
    if sys.platform != 'win32':
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, VALUE_NAME, 0, winreg.REG_SZ, _command())
            else:
                try:
                    winreg.DeleteValue(k, VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


def gamma_unlocked() -> bool | None:
    """True/False — состояние ключа GdiIcmGammaRange, None — прочитать не удалось."""
    if sys.platform != 'win32':
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, ICM_KEY) as k:
            v, _ = winreg.QueryValueEx(k, GAMMA_VAL)
            return int(v) == 256
    except OSError:
        return False


def set_gamma_unlock(on: bool) -> tuple[bool, str]:
    """Записывает/удаляет ключ через reg.exe с повышением прав (UAC)."""
    if sys.platform != 'win32':
        return False, 'Доступно только на Windows'
    if on:
        args = f'add "{ICM_KEY}" /v {GAMMA_VAL} /t REG_DWORD /d 256 /f'
    else:
        args = f'delete "{ICM_KEY}" /v {GAMMA_VAL} /f'
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(None, 'runas', 'reg.exe', args, None, 0)
    except Exception as e:  # pragma: no cover
        return False, str(e)
    if rc > 32:
        return True, ''
    return False, 'Отменено (UAC) или произошла ошибка'
