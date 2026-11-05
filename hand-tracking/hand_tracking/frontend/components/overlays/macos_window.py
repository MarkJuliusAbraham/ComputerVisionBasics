"""A click-through, always-on-top overlay window for macOS, built on AppKit.

Tk cannot make a macOS window ignore the mouse, float over full-screen apps,
or have a transparent background, so this overlay is an AppKit ``NSPanel``
created through pyobjc. On macOS, Tk's event loop runs the Cocoa event loop,
so the panel lives on Tk's (main) thread and needs no loop of its own.

It has the same interface as ``ClickThroughOverlayWindow`` (Windows), so
``HandTrackingOverlay`` works with either.
https://developer.apple.com/documentation/appkit/nspanel
"""

from __future__ import annotations

from collections.abc import Callable
import io
import logging
import tkinter as tk

from PIL import Image

from hand_tracking.backend.settings.overlay_settings import OverlayPosition
from hand_tracking.frontend.components.theme import ThemeMetrics

logger = logging.getLogger(__name__)
SCREEN_MARGIN = 20


class MacOverlayWindow:
    """Show rendered RGBA images in a borderless panel that clicks pass through."""

    def __init__(self, parent: tk.Misc) -> None:
        try:
            import AppKit
        except ImportError as error:
            raise RuntimeError(
                "The macOS overlay needs pyobjc. Install it with: python -m pip install -r requirements.txt"
            ) from error
        self._appkit = AppKit
        self.appearance = ThemeMetrics(parent)
        self.position: OverlayPosition | None = None
        self.background_opacity = 0.94
        self.repositioning = False
        self.on_position_changed: Callable[[OverlayPosition], None] | None = None
        self._renderer: Callable[[float], Image.Image] | None = None
        self._size = (1, 1)
        self._closed = False
        self._panel = self._create_panel()
        logger.info("macOS overlay panel created")

    def _create_panel(self):
        appkit = self._appkit
        style = appkit.NSWindowStyleMaskBorderless | appkit.NSWindowStyleMaskNonactivatingPanel
        panel = appkit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            appkit.NSMakeRect(0, 0, 1, 1), style, appkit.NSBackingStoreBuffered, False,
        )
        panel.setOpaque_(False)
        panel.setBackgroundColor_(appkit.NSColor.clearColor())
        panel.setHasShadow_(False)
        panel.setHidesOnDeactivate_(False)
        panel.setReleasedWhenClosed_(False)
        # Above normal and floating windows, like the Windows topmost overlay.
        panel.setLevel_(appkit.NSStatusWindowLevel)
        # Every space, including over apps in full-screen mode; not in Cmd+` cycling.
        panel.setCollectionBehavior_(
            appkit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | appkit.NSWindowCollectionBehaviorFullScreenAuxiliary
            | appkit.NSWindowCollectionBehaviorStationary
            | appkit.NSWindowCollectionBehaviorIgnoresCycle
        )
        panel.setIgnoresMouseEvents_(True)  # Click-through
        view = appkit.NSImageView.alloc().initWithFrame_(appkit.NSMakeRect(0, 0, 1, 1))
        view.setImageScaling_(appkit.NSImageScaleAxesIndependently)
        view.setEditable_(False)
        panel.setContentView_(view)
        self._view = view
        return panel

    def set_renderer(self, renderer: Callable[[float], Image.Image]) -> None:
        self._renderer = renderer

    def refresh(self) -> None:
        if not self._closed:
            self.appearance.refresh()
            self.redraw()

    def redraw(self) -> None:
        if self._closed or self._renderer is None:
            return
        # At zero opacity, keep a surface to grab while repositioning.
        opacity = max(0.2, self.background_opacity) if self.repositioning else self.background_opacity
        image = self._renderer(opacity)
        resized = image.size != self._size
        self._size = image.size
        if self.position is None:
            screen = self._screen_frame()
            self.position = OverlayPosition(
                int(screen.origin.x + screen.size.width - image.width - SCREEN_MARGIN), SCREEN_MARGIN,
            )
            resized = True
        if resized:
            self.position = self.fit_position(self.position, *self._size)
            self._place()
        self._view.setImage_(self._ns_image(image))

    def _ns_image(self, image: Image.Image):
        """Transfer the RGBA image losslessly through uncompressed TIFF data."""
        buffer = io.BytesIO()
        image.save(buffer, "TIFF")
        data = buffer.getvalue()
        ns_image = self._appkit.NSImage.alloc().initWithData_(
            self._appkit.NSData.dataWithBytes_length_(data, len(data)),
        )
        # Tk and the renderer measure in points on macOS, as AppKit does.
        ns_image.setSize_((image.width, image.height))
        return ns_image

    def _screen_frame(self):
        screen = self._appkit.NSScreen.mainScreen() or self._appkit.NSScreen.screens()[0]
        return screen.visibleFrame()

    def _desktop_height(self) -> float:
        # AppKit measures y upward from the bottom of the first screen; Tk
        # positions, like OverlayPosition, measure downward from its top.
        return self._appkit.NSScreen.screens()[0].frame().size.height

    def _place(self) -> None:
        width, height = self._size
        y = self._desktop_height() - self.position.y - height
        self._panel.setFrame_display_(
            self._appkit.NSMakeRect(self.position.x, y, width, height), True,
        )

    def fit_position(self, position: OverlayPosition, width: int, height: int) -> OverlayPosition:
        """Keep the overlay inside the visible area of the main screen."""
        screen = self._screen_frame()
        top = int(self._desktop_height() - (screen.origin.y + screen.size.height))
        left = int(screen.origin.x)
        right, bottom = left + int(screen.size.width), top + int(screen.size.height)
        return OverlayPosition(
            max(left, min(position.x, right - width)), max(top, min(position.y, bottom - height)),
        )

    def show(self) -> None:
        if self._closed:
            return
        self.refresh()
        self._panel.orderFrontRegardless()

    def hide(self) -> None:
        if not self._closed:
            self._panel.orderOut_(None)

    def set_background_opacity(self, opacity: float) -> None:
        self.background_opacity = opacity
        self.redraw()

    def set_position(self, position: OverlayPosition | None) -> None:
        self.position = None if position is None else self.fit_position(position, *self._size)
        if self.position is not None:
            self._place()
        self.redraw()

    def set_repositioning(self, active: bool) -> None:
        """While repositioning, the panel takes the mouse so it can be dragged."""
        self.repositioning = active
        self._panel.setIgnoresMouseEvents_(not active)
        self._panel.setMovableByWindowBackground_(active)
        if not active:
            self._read_position()
        self.redraw()

    def _read_position(self) -> None:
        frame = self._panel.frame()
        position = OverlayPosition(
            int(frame.origin.x), int(self._desktop_height() - frame.origin.y - frame.size.height),
        )
        if position != self.position:
            self.position = position
            if self.on_position_changed is not None:
                self.on_position_changed(position)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._panel.orderOut_(None)
        self._panel.close()
