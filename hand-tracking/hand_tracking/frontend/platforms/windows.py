"""Windows implementations: OpenCV preview window, DWM title bars, layered overlay."""

from __future__ import annotations

import ctypes
from functools import lru_cache
import os
from pathlib import Path

from .base import FramePreview, InstalledFonts, Platform, TitleBarStyle


class WindowsPlatform(Platform):
    name = "Windows"
    default_camera_index = 1

    def prepare_process(self) -> None:
        """Stop Windows from bitmap-stretching our windows."""
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # system DPI aware
        except (AttributeError, OSError):
            try:
                ctypes.windll.user32.SetProcessDPIAware()  # older Windows fallback
            except (AttributeError, OSError):
                pass

    def create_camera_preview(self) -> FramePreview:
        # OpenCV's window runs on its own thread, so it never competes with Tk.
        from hand_tracking.frontend.camera_preview import CameraPreview
        from hand_tracking.frontend.core.native_window_style import FixedNativeWindowStyle

        return CameraPreview(window_style=FixedNativeWindowStyle())

    def create_title_bar_style(self) -> TitleBarStyle:
        from hand_tracking.frontend.components.themes.title_bar import NativeTitleBarStyle

        return NativeTitleBarStyle()

    def create_overlay_window(self, parent):
        from hand_tracking.frontend.components.overlays.window import ClickThroughOverlayWindow

        return ClickThroughOverlayWindow(parent)

    def installed_fonts(self) -> InstalledFonts:
        return _registry_fonts()


@lru_cache(maxsize=1)
def _registry_fonts() -> InstalledFonts:
    """Font files registered for the machine and the current user."""
    import winreg

    fonts: list[tuple[str, Path]] = []
    registry_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
    folders = (
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts",
    )
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, registry_path) as key:
                for index in range(winreg.QueryInfoKey(key)[1]):
                    name, value, _kind = winreg.EnumValue(key, index)
                    if not isinstance(value, str):
                        continue
                    path = Path(os.path.expandvars(value))
                    candidates = (path,) if path.is_absolute() else tuple(folder / path for folder in folders)
                    for candidate in candidates:
                        if candidate.is_file():
                            fonts.append((name.lower().replace(" (truetype)", ""), candidate))
                            break
        except OSError:
            continue
    return tuple(fonts)
