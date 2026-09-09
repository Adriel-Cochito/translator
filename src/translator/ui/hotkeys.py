from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal
from PySide6.QtWidgets import QApplication, QWidget


MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
VK_L = 0x4C
WM_HOTKEY = 0x0312
HOTKEY_ID = 1


class _HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callback) -> None:  # type: ignore[no-untyped-def]
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, event_type, message):  # type: ignore[no-untyped-def]
        if event_type not in (b"windows_generic_MSG", "windows_generic_MSG"):
            return False, 0
        try:
            msg = wintypes.MSG.from_address(int(message))
        except Exception:
            return False, 0
        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
            self._callback()
        return False, 0


class OverlayHotkey(QObject):
    activated = Signal()

    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self._window = window
        self._filter = _HotkeyFilter(self.activated.emit)
        self._registered = False

    def register(self) -> bool:
        user32 = ctypes.windll.user32
        hwnd = int(self._window.winId())
        ok = bool(user32.RegisterHotKey(hwnd, HOTKEY_ID, MOD_CONTROL | MOD_SHIFT, VK_L))
        self._registered = ok
        instance = QApplication.instance()
        if instance is not None:
            instance.installNativeEventFilter(self._filter)
        return ok

    def unregister(self) -> None:
        if not self._registered:
            return
        ctypes.windll.user32.UnregisterHotKey(int(self._window.winId()), HOTKEY_ID)
        self._registered = False
