"""Windows display scaling setup for the Dear PyGui surface."""

import ctypes
import sys


def enable_dpi_awareness():
    """Stop Windows from bitmap-stretching the control viewport."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass
