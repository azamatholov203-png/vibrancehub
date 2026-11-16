"""Имена процессов: активное окно (для автопереключения) и список запущенных."""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

IS_WIN = sys.platform == 'win32'

_u32 = None
_k32 = None

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TH32CS_SNAPPROCESS = 0x2
INVALID = ~0 & 0xFFFFFFFFFFFFFFFF

MOCK_PROCS = ['cs2.exe', 'steam.exe', 'explorer.exe', 'chrome.exe',
              'escapefromtarkov.exe', 'discord.exe', 'rdr2.exe']


def _dlls():
    global _u32, _k32
    if _u32 is None and IS_WIN:
        _u32 = ctypes.WinDLL('user32')
        _k32 = ctypes.WinDLL('kernel32')
        _u32.GetForegroundWindow.restype = wintypes.HWND
        _u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        _k32.OpenProcess.restype = wintypes.HANDLE
        _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        _k32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD)]
        _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    return _u32, _k32


def get_foreground_process() -> str:
    """Имя exe активного окна в нижнем регистре, '' — если окна нет/недоступно."""
    if not IS_WIN:
        return ''
    u32, k32 = _dlls()
    hwnd = u32.GetForegroundWindow()
    if not hwnd:
        return ''
    pid = wintypes.DWORD(0)
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ''
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not h:
        return ''
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if not k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return ''
        return buf.value.replace('/', '\\').rsplit('\\', 1)[-1].lower()
    finally:
        k32.CloseHandle(h)


class _PE(ctypes.Structure):
    _fields_ = [
        ('dwSize', wintypes.DWORD),
        ('cntUsage', wintypes.DWORD),
        ('th32ProcessID', wintypes.DWORD),
        ('th32DefaultHeapID', ctypes.c_size_t),
        ('th32ModuleID', wintypes.DWORD),
        ('cntThreads', wintypes.DWORD),
        ('th32ParentProcessID', wintypes.DWORD),
        ('pcPriClassBase', ctypes.c_long),
        ('dwFlags', wintypes.DWORD),
        ('szExeFile', ctypes.c_wchar * 260),
    ]


def list_running_processes() -> list[str]:
    """Список имён exe запущенных процессов (нижний регистр, без путей)."""
    if not IS_WIN:
        return sorted(MOCK_PROCS)
    _, k32 = _dlls()
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PE)]
    k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_PE)]
    h = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not h or h == INVALID:
        return []
    out: set[str] = set()
    pe = _PE()
    pe.dwSize = ctypes.sizeof(_PE)
    ok = k32.Process32FirstW(h, ctypes.byref(pe))
    while ok:
        name = pe.szExeFile
        if name:
            out.add(name.lower())
        ok = k32.Process32NextW(h, ctypes.byref(pe))
    k32.CloseHandle(h)
    return sorted(out)


def own_process_names() -> set[str]:
    """Имена процессов самого приложения, чтобы автопереключение их игнорировало."""
    names: set[str] = set()
    if getattr(sys, 'frozen', False):
        names.add(Path(sys.executable).name.lower())
    else:
        names |= {'python.exe', 'pythonw.exe'}
    return names
