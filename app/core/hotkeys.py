"""Глобальные хоткеи: Ctrl+Alt+1..8 — пресеты по слотам, Ctrl+Alt+0 — рабочий стол."""
from __future__ import annotations

import ctypes
import sys
import threading
from ctypes import wintypes

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_ALT = 0x1
MOD_CONTROL = 0x2
MOD_NOREPEAT = 0x4000


class HotkeyManager(threading.Thread):
    """Регистрирует Ctrl+Alt+0..8 в Windows и шлёт id нажатого хоткея в callback.

    Callback вызывается из отдельного потока — оборачивай его в Qt Signal.
    """

    daemon = True

    def __init__(self, on_hotkey) -> None:
        super().__init__(name='vibrancehub-hotkeys')
        self.on_hotkey = on_hotkey
        self._stop_evt = threading.Event()
        self._tid: int | None = None
        self._registered: list[int] = []
        self.failed: list[int] = []

    def run(self) -> None:
        if sys.platform != 'win32':
            return
        k32 = ctypes.WinDLL('kernel32')
        u32 = ctypes.WinDLL('user32')
        self._tid = k32.GetCurrentThreadId()
        u32.RegisterHotKey.restype = wintypes.BOOL
        u32.RegisterHotKey.argtypes = [wintypes.HWND, wintypes.INT, wintypes.UINT, wintypes.UINT]
        u32.UnregisterHotKey.argtypes = [wintypes.HWND, wintypes.INT]
        u32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                    wintypes.UINT, wintypes.UINT]
        self._registered = []
        self.failed = []
        for hid in range(9):                      # id 0..8 -> клавиши 0..8
            vk = ord('0') + hid
            mods = MOD_ALT | MOD_CONTROL | MOD_NOREPEAT
            if u32.RegisterHotKey(None, hid, mods, vk):
                self._registered.append(hid)
            else:
                self.failed.append(hid)
        msg = wintypes.MSG()
        ref = ctypes.byref(msg)
        while not self._stop_evt.is_set():
            r = u32.GetMessageW(ref, None, 0, 0)
            if r <= 0:
                break
            if msg.message == WM_HOTKEY:
                try:
                    self.on_hotkey(int(msg.wParam))
                except Exception:
                    pass
        for hid in self._registered:
            u32.UnregisterHotKey(None, hid)
        self._registered = []

    def stop(self) -> None:
        self._stop_evt.set()
        if self._tid and sys.platform == 'win32':
            k32 = ctypes.WinDLL('kernel32')
            k32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
