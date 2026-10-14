"""A click-through window whose image controls foreground/background opacity."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from PIL import Image

from hand_tracking.ui.components.theme import ThemeMetrics
from hand_tracking.ui.core.idle_refresh import IdleRefresh
from hand_tracking.settings.overlay_settings import OverlayPosition

from .layered_presenter import WindowsLayeredPresenter
from .native_style import WindowsOverlayStyle


class ClickThroughOverlayWindow:
    def __init__(
        self, parent: tk.Misc, *, backend: WindowsOverlayStyle | None = None,
        presenter: WindowsLayeredPresenter | None = None,
    ) -> None:
        self.backend = backend if backend is not None else WindowsOverlayStyle()
        if not self.backend.available:
            raise RuntimeError("Click-through overlays currently require Windows.")
        self._presenter = presenter if presenter is not None else WindowsLayeredPresenter()
        self.window = tk.Toplevel(parent, takefocus=False)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.resizable(False, False)
        self.appearance = ThemeMetrics(self.window)
        self.position: OverlayPosition | None = None
        self.background_opacity = 0.94
        self.repositioning = False
        self.on_position_changed: Callable[[OverlayPosition], None] | None = None
        self._renderer: Callable[[float], Image.Image] | None = None
        self._image: Image.Image | None = None
        self._handle: int | None = None
        self._drag_offset: tuple[int, int] | None = None
        self._closed = False
        self._size = (1, 1)
        self._refresh = IdleRefresh(self.window, self.refresh, event="<<ThemeChanged>>")
        self.window.bind("<Map>", self._mapped, add="+")
        self.window.bind("<ButtonPress-1>", self._begin_drag)
        self.window.bind("<B1-Motion>", self._drag)
        self.window.bind("<ButtonRelease-1>", self._finish_drag)

    def set_renderer(self, renderer: Callable[[float], Image.Image]) -> None:
        self._renderer = renderer

    def _apply_native_style(self) -> int:
        handle = self.backend.handle(self.window)
        self._handle = self.backend.apply(
            self.window, click_through=not self.repositioning,
            reset_layered=handle != self._handle,
        )
        return self._handle

    def refresh(self) -> None:
        if not self._closed:
            self.appearance.refresh()
            self.redraw()

    def redraw(self) -> None:
        if self._closed or self._renderer is None:
            return
        # At zero opacity, provide a temporary drag surface while repositioning.
        opacity = max(0.2, self.background_opacity) if self.repositioning else self.background_opacity
        image = self._renderer(opacity)
        resized = image.size != self._size
        self._image = image
        self._size = image.size
        if self.position is None:
            margin = self.appearance.pixels(20)
            self.position = OverlayPosition(
                max(0, self.window.winfo_screenwidth() - image.width - margin), margin,
            )
            resized = True
        if resized:
            self.position = self.backend.fit_position(self.position, *self._size)
            self.window.geometry(f"{image.width}x{image.height}")
            self.window.update_idletasks()
        self._present_image()

    def _present_image(self) -> None:
        if self._image is not None and self.position is not None and not self._closed:
            self._presenter.present(self._apply_native_style(), self._image, self.position)

    def show(self) -> None:
        self.refresh()
        self.window.deiconify()
        self._present_image()

    def _mapped(self, event: tk.Event[tk.Misc]) -> None:
        if event.widget is self.window:
            self._present_image()

    def set_background_opacity(self, opacity: float) -> None:
        self.background_opacity = opacity
        self.redraw()

    def set_position(self, position: OverlayPosition | None) -> None:
        self.position = position
        if position is not None:
            self.position = self.backend.fit_position(position, *self._size)
        self.redraw()

    def set_repositioning(self, active: bool) -> None:
        self.repositioning = active
        self._drag_offset = None
        self.window.configure(cursor="fleur" if active else "")
        self.redraw()

    def _begin_drag(self, event: tk.Event[tk.Misc]) -> str | None:
        if self.repositioning and self.position is not None:
            self._drag_offset = (event.x_root - self.position.x, event.y_root - self.position.y)
            return "break"
        return None

    def _drag(self, event: tk.Event[tk.Misc]) -> str | None:
        if self._drag_offset is not None:
            self.position = OverlayPosition(
                event.x_root - self._drag_offset[0], event.y_root - self._drag_offset[1],
            )
            # Moving uses native placement; it does not rasterize the report.
            self.backend.position(self.window, self.position.x, self.position.y, *self._size)
            return "break"
        return None

    def _finish_drag(self, _event: tk.Event[tk.Misc]) -> str | None:
        if self._drag_offset is not None:
            self._drag_offset = None
            if self.on_position_changed is not None and self.position is not None:
                self.on_position_changed(self.position)
            return "break"
        return None

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._presenter.close()
            self.window.destroy()
