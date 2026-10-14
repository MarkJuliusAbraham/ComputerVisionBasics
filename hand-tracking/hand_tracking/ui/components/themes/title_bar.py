"""Apply theme colors to native Windows title bars without replacing the frame.

Caption/text/border colors require Windows 11; unsupported attributes are ignored.
https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute
"""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import sys
import tkinter as tk
from weakref import WeakKeyDictionary

from hand_tracking.ui.core import win32
from hand_tracking.ui.core.widget_tree import root_service, walk_widgets


@dataclass(frozen=True)
class TitleBarPalette:
    background: str
    foreground: str
    border: str
    dark: bool


class NativeTitleBarStyle:
    USE_IMMERSIVE_DARK_MODE = 20
    BORDER_COLOR = 34
    CAPTION_COLOR = 35
    TEXT_COLOR = 36

    def __init__(self):
        self._dwm = None
        if sys.platform != "win32":
            return
        try:
            self._user32 = win32.user32()
            dwm = ctypes.WinDLL("dwmapi", use_last_error=True)
            dwm.DwmSetWindowAttribute.argtypes = (
                wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
            )
            dwm.DwmSetWindowAttribute.restype = ctypes.c_int32
            self._dwm = dwm
        except (OSError, AttributeError):
            pass

    @property
    def available(self):
        return self._dwm is not None

    def handle(self, window):
        # Tk's widget handle belongs to its client area. DWM needs the outer
        # window handle; pointer-sized signatures prevent truncation on x64.
        return self._user32.GetAncestor(window.winfo_id(), win32.GA_ROOT)

    def apply(self, window, handle, palette):
        attributes = (
            (self.USE_IMMERSIVE_DARK_MODE, wintypes.BOOL(palette.dark)),
            (self.CAPTION_COLOR, self._color(window, palette.background)),
            (self.TEXT_COLOR, self._color(window, palette.foreground)),
            (self.BORDER_COLOR, self._color(window, palette.border)),
        )
        # Unsupported DWM attributes return an HRESULT rather than raising.
        # Do not change position, focus, resizing, or native window controls.
        for attribute, value in attributes:
            self._dwm.DwmSetWindowAttribute(
                handle, attribute, ctypes.byref(value), ctypes.sizeof(value),
            )

    @staticmethod
    def _color(window, color):
        red, green, blue = (channel // 257 for channel in window.winfo_rgb(color))
        return wintypes.DWORD(red | (green << 8) | (blue << 16))


class TitleBarTheme:
    """Share title-bar styling across the hub, tracking windows, and dialogs."""

    def __init__(self, root, palette_provider, backend=None):
        self.root = root
        self.palette_provider = palette_provider
        self.backend = backend if backend is not None else NativeTitleBarStyle()
        self._applied = WeakKeyDictionary()
        self._pending = set()
        self._refresh_pending = False
        if self.backend.available:
            root.bind("<Map>", self._on_map, add="+")
            root.bind_class("Toplevel", "<Map>", self._on_map, add="+")

    @classmethod
    def for_root(cls, root, palette_provider):
        return root_service(root, "_title_bar_theme", lambda owner: cls(owner, palette_provider))

    def refresh(self):
        if self.backend.available and not self._refresh_pending:
            # Sun Valley finishes its native palette through ThemeChanged.
            # Wait for that event before sampling the painted surface colors.
            self._refresh_pending = True
            self.root.after_idle(self._refresh)

    def _refresh(self):
        self._refresh_pending = False
        for widget in walk_widgets(self.root):
            if isinstance(widget, (tk.Tk, tk.Toplevel)):
                self._apply(widget)

    def _on_map(self, event):
        window = event.widget
        if isinstance(window, (tk.Tk, tk.Toplevel)) and window not in self._pending:
            self._pending.add(window)
            self.root.after_idle(self._apply_pending, window)

    def _apply_pending(self, window):
        self._pending.discard(window)
        self._apply(window)

    def _apply(self, window):
        try:
            if (not window.winfo_exists() or not window.winfo_ismapped()
                    or window.overrideredirect()):
                return
            handle = self.backend.handle(window)
            if not handle:
                return
            palette = self.palette_provider()
            snapshot = (handle, palette)
            if self._applied.get(window) != snapshot:
                self.backend.apply(window, handle, palette)
                self._applied[window] = snapshot
        except (tk.TclError, OSError):
            # A dialog can close before its queued Map callback is delivered.
            pass
