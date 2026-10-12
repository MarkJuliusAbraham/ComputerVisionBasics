"""Windows styles for fixed native windows that are not managed by Tk."""

import ctypes
from ctypes import wintypes
import sys


class FixedNativeWindowStyle:
    GWL_STYLE = -16
    WS_MAXIMIZEBOX = 0x00010000
    WS_THICKFRAME = 0x00040000
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    SWP_FRAMECHANGED = 0x0020

    def __init__(self):
        self._user32 = None
        if sys.platform != "win32":
            return
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._user32.FindWindowExW.argtypes = (
            wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR,
        )
        self._user32.FindWindowExW.restype = wintypes.HWND
        self._user32.GetWindowThreadProcessId.argtypes = (
            wintypes.HWND, ctypes.POINTER(wintypes.DWORD),
        )
        self._user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self._kernel32.GetCurrentThreadId.argtypes = ()
        self._kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        self._get_style = getattr(self._user32, "GetWindowLongPtrW", self._user32.GetWindowLongW)
        self._set_style = getattr(self._user32, "SetWindowLongPtrW", self._user32.SetWindowLongW)
        self._get_style.argtypes = (wintypes.HWND, ctypes.c_int)
        self._get_style.restype = ctypes.c_ssize_t
        self._set_style.argtypes = (
            wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t,
        )
        self._set_style.restype = ctypes.c_ssize_t
        self._user32.SetWindowPos.argtypes = (
            wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, wintypes.UINT,
        )
        self._user32.SetWindowPos.restype = wintypes.BOOL

    def apply(self, title):
        """Disable resizing/maximization without changing position or focus.

        Run on the window's owner thread. Matching both title and thread avoids
        touching a similarly named window in another running app instance.
        """
        if self._user32 is None:
            return
        owner = self._kernel32.GetCurrentThreadId()
        handle = None
        while True:
            handle = self._user32.FindWindowExW(None, handle, None, title)
            if not handle:
                raise RuntimeError(f"Could not find the native window: {title}")
            if self._user32.GetWindowThreadProcessId(handle, None) == owner:
                break
        style = self._get_style(handle, self.GWL_STYLE)
        fixed_style = style & ~(self.WS_MAXIMIZEBOX | self.WS_THICKFRAME)
        ctypes.set_last_error(0)
        if not self._set_style(handle, self.GWL_STYLE, fixed_style):
            if ctypes.get_last_error():
                raise ctypes.WinError(ctypes.get_last_error())
        flags = (
            self.SWP_NOSIZE | self.SWP_NOMOVE | self.SWP_NOZORDER
            | self.SWP_NOACTIVATE | self.SWP_FRAMECHANGED
        )
        if not self._user32.SetWindowPos(handle, None, 0, 0, 0, 0, flags):
            raise ctypes.WinError(ctypes.get_last_error())
