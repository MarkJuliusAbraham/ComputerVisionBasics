import ctypes
import sys


def enable_dpi_awareness():
    """Stop Windows from bitmap-stretching our windows. Call before creating any window."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # system DPI aware
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # older Windows fallback
        except (AttributeError, OSError):
            pass