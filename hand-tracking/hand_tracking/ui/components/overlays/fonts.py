"""Resolve the active Tk theme's font into a pixel-sized FreeType font."""

from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import sys

from PIL import ImageFont

from hand_tracking.ui.components.theme import ThemeMetrics


class OverlayFontProvider:
    def __init__(self, appearance: ThemeMetrics) -> None:
        self.appearance = appearance

    def font(self, *, bold: bool = False) -> ImageFont.FreeTypeFont:
        actual = self.appearance.font.actual()
        size = int(actual["size"])
        pixels = abs(size) if size < 0 else round(
            size * float(self.appearance.widget.tk.call("tk", "scaling")),
        )
        return self._load(str(actual["family"]), max(1, pixels), bold or actual["weight"] == "bold")

    @staticmethod
    @lru_cache(maxsize=1)
    def _installed_fonts() -> tuple[tuple[str, Path], ...]:
        if sys.platform != "win32":
            return ()
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

    @classmethod
    @lru_cache(maxsize=32)
    def _load(cls, family: str, size: int, bold: bool) -> ImageFont.FreeTypeFont:
        fonts = cls._installed_fonts()
        for candidate_family in (family.lower(), "segoe ui", "arial"):
            desired = candidate_family + (" bold" if bold else "")
            paths = [path for name, path in fonts if name == desired]
            paths.extend(path for name, path in fonts if name == candidate_family and path not in paths)
            for path in paths:
                try:
                    font = ImageFont.truetype(str(path), size)
                    if bold:
                        try:
                            font.set_variation_by_name("Bold")
                        except (OSError, ValueError):
                            pass  # Static fonts have no variation axes.
                    return font
                except OSError:
                    continue
        raise RuntimeError(f"Cannot load a system font for the overlay ({family}).")
