"""Present an RGBA image using Windows' per-pixel-alpha compositor.

No color key or global alpha is applied: the image owns each pixel's opacity.
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-updatelayeredwindow
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

from PIL import Image

from gui_tkinter.core import win32
from settings.overlay_settings import OverlayPosition


class _BitmapInfoHeader(ctypes.Structure):
    _fields_ = (
        ("size", wintypes.DWORD), ("width", wintypes.LONG),
        ("height", wintypes.LONG), ("planes", wintypes.WORD),
        ("bits_per_pixel", wintypes.WORD), ("compression", wintypes.DWORD),
        ("image_size", wintypes.DWORD), ("x_density", wintypes.LONG),
        ("y_density", wintypes.LONG), ("colors_used", wintypes.DWORD),
        ("colors_important", wintypes.DWORD),
    )


class _BitmapInfo(ctypes.Structure):
    _fields_ = (("header", _BitmapInfoHeader), ("colors", wintypes.DWORD * 1))


class _BlendFunction(ctypes.Structure):
    _fields_ = (
        ("operation", wintypes.BYTE), ("flags", wintypes.BYTE),
        ("opacity", wintypes.BYTE), ("alpha_format", wintypes.BYTE),
    )


class WindowsLayeredPresenter:
    """Reuse one native bitmap and DC until the overlay changes size."""

    def __init__(self) -> None:
        self._user32 = win32.require_user32("Per-pixel desktop overlays")
        self._gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        self._bind_functions()
        self._dc = self._gdi32.CreateCompatibleDC(None)
        win32.check(self._dc)
        self._bitmap: int | None = None
        self._previous_bitmap: int | None = None
        self._bits = ctypes.c_void_p()
        self._size = (0, 0)

    def _bind_functions(self) -> None:
        gdi = self._gdi32
        gdi.CreateCompatibleDC.argtypes = (wintypes.HDC,)
        gdi.CreateCompatibleDC.restype = wintypes.HDC
        gdi.CreateDIBSection.argtypes = (
            wintypes.HDC, ctypes.POINTER(_BitmapInfo), wintypes.UINT,
            ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD,
        )
        gdi.CreateDIBSection.restype = wintypes.HBITMAP
        gdi.SelectObject.argtypes = (wintypes.HDC, wintypes.HANDLE)
        gdi.SelectObject.restype = wintypes.HANDLE
        gdi.DeleteObject.argtypes = (wintypes.HANDLE,)
        gdi.DeleteObject.restype = wintypes.BOOL
        gdi.DeleteDC.argtypes = (wintypes.HDC,)
        gdi.DeleteDC.restype = wintypes.BOOL
        self._user32.UpdateLayeredWindow.argtypes = (
            wintypes.HWND, wintypes.HDC, ctypes.POINTER(wintypes.POINT),
            ctypes.POINTER(wintypes.SIZE), wintypes.HDC,
            ctypes.POINTER(wintypes.POINT), wintypes.DWORD,
            ctypes.POINTER(_BlendFunction), wintypes.DWORD,
        )
        self._user32.UpdateLayeredWindow.restype = wintypes.BOOL

    def _resize_bitmap(self, width: int, height: int) -> None:
        if self._size == (width, height):
            return
        self._release_bitmap()
        info = _BitmapInfo()
        info.header = _BitmapInfoHeader(
            ctypes.sizeof(_BitmapInfoHeader), width, -height, 1, 32, 0,
            width * height * 4, 0, 0, 0, 0,
        )
        bitmap = self._gdi32.CreateDIBSection(
            self._dc, ctypes.byref(info), 0, ctypes.byref(self._bits), None, 0,
        )
        win32.check(bitmap)
        previous = self._gdi32.SelectObject(self._dc, bitmap)
        if not previous or previous == ctypes.c_void_p(-1).value:
            self._gdi32.DeleteObject(bitmap)
            raise ctypes.WinError(ctypes.get_last_error())
        self._bitmap, self._previous_bitmap = bitmap, previous
        self._size = (width, height)

    def present(self, handle: int, image: Image.Image, position: OverlayPosition) -> None:
        if not self._dc:
            return
        if image.mode != "RGBA":
            raise ValueError("A layered overlay requires an RGBA image.")
        width, height = image.size
        self._resize_bitmap(width, height)
        # Pillow's BGRa packer premultiplies RGB by alpha exactly once, as
        # AC_SRC_ALPHA requires. BGRA would leave colored fringes at the edges.
        pixels = image.tobytes("raw", "BGRa")
        ctypes.memmove(self._bits, pixels, len(pixels))
        destination = wintypes.POINT(position.x, position.y)
        size = wintypes.SIZE(width, height)
        origin = wintypes.POINT(0, 0)
        blend = _BlendFunction(0, 0, 255, 1)  # AC_SRC_OVER, AC_SRC_ALPHA
        win32.check(self._user32.UpdateLayeredWindow(
            handle, None, ctypes.byref(destination), ctypes.byref(size),
            self._dc, ctypes.byref(origin), 0, ctypes.byref(blend), 2,  # ULW_ALPHA
        ))

    def _release_bitmap(self) -> None:
        if self._bitmap:
            self._gdi32.SelectObject(self._dc, self._previous_bitmap)
            self._gdi32.DeleteObject(self._bitmap)
        self._bitmap = self._previous_bitmap = None
        self._bits = ctypes.c_void_p()
        self._size = (0, 0)

    def close(self) -> None:
        if self._dc:
            self._release_bitmap()
            self._gdi32.DeleteDC(self._dc)
            self._dc = None
