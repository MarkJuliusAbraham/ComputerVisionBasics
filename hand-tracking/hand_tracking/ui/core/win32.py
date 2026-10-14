"""Shared Windows API bindings for native window styling.

``user32`` is loaded once per process and its functions get pointer-sized
signatures here, so overlay, title-bar, and fixed-window code do not each
declare them. Importing this module is safe on any platform; ``user32()``
returns None when not running on Windows.

https://learn.microsoft.com/en-us/windows/win32/api/winuser/
"""

import ctypes
from ctypes import wintypes
from functools import lru_cache
import sys

GA_ROOT = 2
GWL_STYLE = -16
GWL_EXSTYLE = -20
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
MONITOR_DEFAULTTONEAREST = 2


class MonitorInfo(ctypes.Structure):
    _fields_ = (
        ("size", wintypes.DWORD), ("monitor", wintypes.RECT),
        ("work", wintypes.RECT), ("flags", wintypes.DWORD),
    )


def _bind(function, argtypes, restype):
    function.argtypes = argtypes
    function.restype = restype
    return function


@lru_cache(maxsize=1)
def user32():
    """The process's user32 library with typed signatures, or None off Windows."""
    if sys.platform != "win32":
        return None
    dll = ctypes.WinDLL("user32", use_last_error=True)
    _bind(dll.GetAncestor, (wintypes.HWND, wintypes.UINT), wintypes.HWND)
    _bind(dll.SetWindowPos, (
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ), wintypes.BOOL)
    _bind(dll.FindWindowExW, (
        wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR,
    ), wintypes.HWND)
    _bind(dll.GetWindowThreadProcessId, (wintypes.HWND, ctypes.POINTER(wintypes.DWORD)), wintypes.DWORD)
    _bind(dll.MonitorFromRect, (ctypes.POINTER(wintypes.RECT), wintypes.DWORD), wintypes.HANDLE)
    _bind(dll.GetMonitorInfoW, (wintypes.HANDLE, ctypes.POINTER(MonitorInfo)), wintypes.BOOL)
    # 32-bit user32 exports only the Long variants; the Ptr names are macros there.
    dll.get_window_long = _bind(
        getattr(dll, "GetWindowLongPtrW", None) or dll.GetWindowLongW,
        (wintypes.HWND, ctypes.c_int), ctypes.c_ssize_t,
    )
    dll.set_window_long = _bind(
        getattr(dll, "SetWindowLongPtrW", None) or dll.SetWindowLongW,
        (wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t), ctypes.c_ssize_t,
    )
    return dll


def require_user32(feature):
    dll = user32()
    if dll is None:
        raise RuntimeError(f"{feature} currently require Windows.")
    return dll


def check(succeeded):
    """Raise the thread's last Windows error when a call reports failure."""
    if not succeeded:
        raise ctypes.WinError(ctypes.get_last_error())


def call_allowing_zero(function, *args):
    """Call an API whose valid result may be 0; fail only if it set an error."""
    ctypes.set_last_error(0)
    result = function(*args)
    if result == 0 and ctypes.get_last_error():
        raise ctypes.WinError(ctypes.get_last_error())
    return result


def root_handle(window):
    """The outer native window that owns a Tk window's client area."""
    handle = require_user32("Native window styling").GetAncestor(window.winfo_id(), GA_ROOT)
    check(handle)
    return handle
