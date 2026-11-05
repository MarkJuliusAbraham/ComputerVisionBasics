"""macOS implementations: native overlay, font discovery, and keeping the app out of App Nap."""

from __future__ import annotations

from functools import lru_cache
import logging
from pathlib import Path

from .base import InstalledFonts, Platform

logger = logging.getLogger(__name__)

FONT_FOLDERS = (
    Path("/System/Library/Fonts"),
    Path("/System/Library/Fonts/Supplemental"),
    Path("/Library/Fonts"),
    Path.home() / "Library" / "Fonts",
)
REGULAR_STYLES = {"regular", "roman", "book", "normal", ""}


class MacPlatform(Platform):
    name = "macOS"

    def __init__(self) -> None:
        self._activity = None

    def prepare_process(self) -> None:
        """Ask macOS not to throttle tracking while the app is in the background.

        App Nap slows timers of apps the user is not looking at, which would
        slow the frame loop while you work in another app. Requires pyobjc.
        """
        try:
            from Foundation import NSProcessInfo
            import Foundation
        except ImportError:
            logger.warning(
                "pyobjc is not installed; macOS may slow hand tracking while the app is in the background."
            )
            return
        options = (
            getattr(Foundation, "NSActivityUserInitiatedAllowingIdleSystemSleep", 0x00EFFFFF)
            | getattr(Foundation, "NSActivityLatencyCritical", 0xFF00000000)
        )
        # The returned token must stay referenced for the activity to last.
        self._activity = NSProcessInfo.processInfo().beginActivityWithOptions_reason_(
            options, "Hand tracking reads the camera continuously",
        )

    def create_overlay_window(self, parent):
        # Native AppKit panel: click-through, transparent, over full-screen apps.
        from hand_tracking.frontend.components.overlays.macos_window import MacOverlayWindow

        return MacOverlayWindow(parent)

    def installed_fonts(self) -> InstalledFonts:
        return _folder_fonts(FONT_FOLDERS)


@lru_cache(maxsize=1)
def _folder_fonts(folders: tuple[Path, ...]) -> InstalledFonts:
    """(lowercase "family style" name, file) pairs, read from each font's own names."""
    from PIL import ImageFont

    fonts: list[tuple[str, Path]] = []
    for folder in folders:
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() not in {".ttf", ".otf", ".ttc"}:
                continue
            try:
                family, style = ImageFont.truetype(str(path), 12).getname()
            except OSError:
                continue
            style = (style or "").lower()
            name = family.lower() if style in REGULAR_STYLES else f"{family} {style}".lower()
            fonts.append((name, path))
    return tuple(fonts)
