"""Windows support for overlays that pass mouse input to other applications.

https://learn.microsoft.com/en-us/windows/win32/winmsg/window-features
"""

import ctypes
from ctypes import wintypes
import tkinter as tk

from hand_tracking.frontend.core import win32
from hand_tracking.backend.settings.overlay_settings import OverlayPosition


class WindowsOverlayStyle:
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    WS_EX_LAYERED = 0x00080000
    WS_EX_NOACTIVATE = 0x08000000

    def __init__(self) -> None:
        self._user32 = win32.user32()

    @property
    def available(self) -> bool:
        return self._user32 is not None

    def handle(self, window: tk.Toplevel) -> int:
        win32.require_user32("Click-through overlays")
        return win32.root_handle(window)

    def apply(
        self, window: tk.Toplevel, *, click_through: bool = True, reset_layered: bool = False,
    ) -> int:
        assert self._user32 is not None
        handle = self.handle(window)
        set_style = self._user32.set_window_long
        previous = win32.call_allowing_zero(self._user32.get_window_long, handle, win32.GWL_EXSTYLE)
        style = (previous & ~self.WS_EX_APPWINDOW) | (
            self.WS_EX_LAYERED
            | self.WS_EX_NOACTIVATE | self.WS_EX_TOOLWINDOW
        )
        if click_through:
            style |= self.WS_EX_TRANSPARENT
        else:
            style &= ~self.WS_EX_TRANSPARENT
        if reset_layered and previous & self.WS_EX_LAYERED:
            # SetLayeredWindowAttributes (including Tk's alpha/color key) and
            # UpdateLayeredWindow cannot be mixed. Reset once per native HWND.
            win32.call_allowing_zero(set_style, handle, win32.GWL_EXSTYLE, previous & ~self.WS_EX_LAYERED)
        changed = style != previous or reset_layered
        if changed:
            win32.call_allowing_zero(set_style, handle, win32.GWL_EXSTYLE, style)
        flags = win32.SWP_NOMOVE | win32.SWP_NOSIZE | win32.SWP_NOACTIVATE
        if changed:
            flags |= win32.SWP_FRAMECHANGED
        win32.check(self._user32.SetWindowPos(handle, win32.HWND_TOPMOST, 0, 0, 0, 0, flags))
        return handle

    def position(self, window: tk.Toplevel, x: int, y: int, width: int, height: int) -> None:
        """Use absolute desktop coordinates, including monitors left of primary."""
        assert self._user32 is not None
        win32.check(self._user32.SetWindowPos(
            self.handle(window), win32.HWND_TOPMOST, x, y, width, height, win32.SWP_NOACTIVATE,
        ))

    def fit_position(self, position: OverlayPosition, width: int, height: int) -> OverlayPosition:
        """Keep a restored/resized overlay within the nearest monitor's work area."""
        assert self._user32 is not None
        rectangle = wintypes.RECT(position.x, position.y, position.x + width, position.y + height)
        monitor = self._user32.MonitorFromRect(ctypes.byref(rectangle), win32.MONITOR_DEFAULTTONEAREST)
        info = win32.MonitorInfo()
        info.size = ctypes.sizeof(info)
        win32.check(monitor and self._user32.GetMonitorInfoW(monitor, ctypes.byref(info)))
        return OverlayPosition(
            max(info.work.left, min(position.x, info.work.right - width)),
            max(info.work.top, min(position.y, info.work.bottom - height)),
        )
