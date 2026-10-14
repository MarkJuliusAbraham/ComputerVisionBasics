"""Own the overlay lifecycle while sharing the debugging report data."""

from collections.abc import Callable
import tkinter as tk

from gui_tkinter.components.overlays.window import ClickThroughOverlayWindow
from settings.overlay_settings import OverlayPosition, OverlaySettings

from .options_dialog import OverlayOptionsDialog
from .renderer import HandOverlayRenderer

from ..debug_panel.live_hand_data import LiveHandData


class HandTrackingOverlay:
    def __init__(
        self, parent: tk.Misc, *, max_deviation: float,
        preferences: OverlaySettings = OverlaySettings(),
        on_save: Callable[[OverlaySettings], None] | None = None,
        window_factory: Callable[[tk.Misc], ClickThroughOverlayWindow] = ClickThroughOverlayWindow,
    ) -> None:
        self.parent = parent
        self._window_factory = window_factory
        self._window: ClickThroughOverlayWindow | None = None
        self._data = LiveHandData()
        self._max_deviation = max_deviation
        self._preferences = self.saved_preferences = preferences
        self._position = preferences.position
        self._on_save = on_save
        self._options: OverlayOptionsDialog | None = None

    @property
    def enabled(self) -> bool:
        return self._window is not None

    def enable(self) -> None:
        if self.enabled:
            return
        window = self._window_factory(self.parent)
        try:
            renderer = HandOverlayRenderer(window.appearance)
            window.set_renderer(lambda opacity: renderer.render(
                self._data, style=self._preferences.style, opacity=opacity,
                max_deviation=self._max_deviation,
            ))
            window.position = self._position
            window.background_opacity = self._preferences.background_opacity
            window.on_position_changed = self._position_changed
            window.show()
        except Exception:
            window.close()
            raise
        self._window = window
        if self._options is not None:
            self._options.set_enabled(True)

    def show_options(self, parent: tk.Misc) -> None:
        if self._options is not None:
            self._options.window.lift()
            return
        self._options = OverlayOptionsDialog(
            parent, self._preferences, on_preview=self.set_preferences,
            on_save=self._save_preferences, on_reposition=self.set_repositioning,
            on_close=self._options_closed, enabled=self.enabled,
        )

    def _options_closed(self) -> None:
        self._options = None

    def set_repositioning(self, active: bool) -> None:
        if self._window is not None:
            self._window.set_repositioning(active)

    def _position_changed(self, position: OverlayPosition) -> None:
        self._position = position
        if self._options is not None:
            self._options.set_position(position)

    def set_preferences(self, preferences: OverlaySettings) -> None:
        previous = self._preferences
        self._preferences = preferences
        if preferences.position != previous.position:
            self._position = preferences.position
        if self._window is None:
            return
        self._window.background_opacity = preferences.background_opacity
        if preferences.position != previous.position:
            self._window.set_position(self._position)
        else:
            self._window.refresh()

    def _save_preferences(self, preferences: OverlaySettings) -> None:
        if self._on_save is not None:
            self._on_save(preferences)
        self.saved_preferences = preferences

    def load_preferences(self, preferences: OverlaySettings) -> None:
        self.set_preferences(preferences)
        self.saved_preferences = preferences
        if self._options is not None:
            self._options.accept(preferences)

    def confirm_close(self) -> bool:
        return self._options is None or self._options.confirm_close()

    def update_data(self, data: LiveHandData) -> None:
        self._data = data
        if self._window is not None:
            self._window.redraw()

    def set_display(self, max_deviation: float) -> None:
        self._max_deviation = max_deviation
        self.refresh()

    def refresh(self) -> None:
        if self._window is not None:
            self._window.refresh()

    def close(self) -> None:
        if self._window is not None:
            self._window.close()
            self._window = None
        if self._options is not None:
            self._options.set_enabled(False)

    def shutdown(self) -> None:
        if self._options is not None:
            self._options.destroy()
        self.close()
