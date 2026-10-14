"""Windows styles for fixed native windows that are not managed by Tk."""

import ctypes

from . import win32


class FixedNativeWindowStyle:
    WS_MAXIMIZEBOX = 0x00010000
    WS_THICKFRAME = 0x00040000

    def __init__(self):
        self._user32 = win32.user32()
        self._kernel32 = None
        if self._user32 is not None:
            self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self._kernel32.GetCurrentThreadId.argtypes = ()
            self._kernel32.GetCurrentThreadId.restype = ctypes.c_ulong

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
        style = self._user32.get_window_long(handle, win32.GWL_STYLE)
        fixed_style = style & ~(self.WS_MAXIMIZEBOX | self.WS_THICKFRAME)
        win32.call_allowing_zero(self._user32.set_window_long, handle, win32.GWL_STYLE, fixed_style)
        flags = (
            win32.SWP_NOSIZE | win32.SWP_NOMOVE | win32.SWP_NOZORDER
            | win32.SWP_NOACTIVATE | win32.SWP_FRAMECHANGED
        )
        win32.check(self._user32.SetWindowPos(handle, None, 0, 0, 0, 0, flags))
