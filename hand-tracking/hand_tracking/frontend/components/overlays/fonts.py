"""Resolve the active Tk theme's font into a pixel-sized FreeType font."""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from hand_tracking.frontend.components.theme import ThemeMetrics


InstalledFonts = tuple[tuple[str, Path], ...]


class OverlayFontProvider:
    """``installed_fonts`` comes from the Platform: (lowercase family, file) pairs."""

    def __init__(
        self, appearance: ThemeMetrics, installed_fonts: Callable[[], InstalledFonts] = tuple,
    ) -> None:
        self.appearance = appearance
        self.installed_fonts = installed_fonts

    def font(self, *, bold: bool = False) -> ImageFont.FreeTypeFont:
        actual = self.appearance.font.actual()
        size = int(actual["size"])
        pixels = abs(size) if size < 0 else round(
            size * float(self.appearance.widget.tk.call("tk", "scaling")),
        )
        return self._load(
            self.installed_fonts(), str(actual["family"]), max(1, pixels), bold or actual["weight"] == "bold",
        )

    @staticmethod
    @lru_cache(maxsize=32)
    def _load(fonts: InstalledFonts, family: str, size: int, bold: bool) -> ImageFont.FreeTypeFont:
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
        # No matching system font (none found, or an unusual system): Pillow's
        # bundled font keeps the overlay readable instead of failing.
        return ImageFont.load_default(size=size)
