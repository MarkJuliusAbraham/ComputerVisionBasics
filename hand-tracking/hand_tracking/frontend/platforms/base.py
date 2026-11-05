"""Everything the frontend does differently per operating system, in one place.

``main.py`` picks one ``Platform`` with ``current_platform`` and hands it to
the components that need it. Components never check ``sys.platform``; the only
other checks are the Windows API binding (``core/win32.py``), which refuses to
load elsewhere, and saved-path portability (``project_paths.py``), which is
about where a file was written rather than where the app runs. The base
class is the portable behaviour, which is what macOS uses. ``WindowsPlatform``
overrides the parts that have native Windows implementations. Supporting
another system, or a native macOS feature, means changing one class.

Implementations are imported inside methods so that loading a platform never
imports another system's native bindings.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import tkinter as tk

    from hand_tracking.frontend.components.overlays.window import ClickThroughOverlayWindow


class FramePreview(Protocol):
    """A window showing the annotated camera frame."""

    def attach(self, parent) -> None: ...
    def set_visible(self, visible: bool) -> None: ...
    def show(self, frame) -> None: ...
    def close(self) -> None: ...


class TitleBarStyle(Protocol):
    """Native title-bar coloring; ``available`` is False where there is none."""

    @property
    def available(self) -> bool: ...
    def handle(self, window): ...
    def apply(self, window, handle, palette) -> None: ...


InstalledFonts = tuple[tuple[str, Path], ...]


class Platform:
    """Portable defaults: Tk drawing, no native window styling, no desktop overlay."""

    name = "Portable"
    # The built-in camera is usually index 0.
    default_camera_index = 0

    def prepare_process(self) -> None:
        """Process-wide setup to run before any window is created."""

    def create_camera_preview(self) -> FramePreview:
        # Some systems (macOS) only allow windows on the main thread, which Tk
        # owns, so the preview is drawn with Tk on that thread.
        from hand_tracking.frontend.tk_camera_preview import TkCameraPreview

        return TkCameraPreview()

    def create_title_bar_style(self) -> TitleBarStyle:
        from hand_tracking.frontend.components.themes.title_bar import NoTitleBarStyle

        return NoTitleBarStyle()

    def create_overlay_window(self, parent: tk.Misc) -> ClickThroughOverlayWindow:
        raise RuntimeError(f"The desktop overlay is not available on {self.name}; it requires Windows.")

    def installed_fonts(self) -> InstalledFonts:
        """(lowercase family name, font file) pairs for drawing overlay text."""
        return ()

