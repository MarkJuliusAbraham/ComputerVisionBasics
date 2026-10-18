"""Composition of hand tracking panels, independent of the hub's layout."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from dataclasses import dataclass
from typing import Callable

from hand_tracking.backend.gestures.gesture_config import GestureConfig
from hand_tracking.frontend.core.callbacks import Action, ApplySettingsCallback
from hand_tracking.frontend.core.state import ControlCallbacks, PanelSet, WindowContext
from hand_tracking.frontend.tracking.window import TrackingWindow
from hand_tracking.backend.landmarker.model_asset import HandLandmarkerAsset
from hand_tracking.backend.settings.settings_manager import Settings
from hand_tracking.backend.settings.overlay_settings import OverlaySettings

from .debug_panel.debug_panel import HandDebugPanel
from .live_pose_feed import LivePoseFeed
from .mapping_panel.mapping_panel import MappingPanel
from .overlay.hand_tracking_overlay import HandTrackingOverlay
from .settings_panel.settings_panel import HandSettingsPanel


@dataclass(frozen=True)
class HandTrackingActions:
    restart: Action
    toggle_pause: Action
    activity_changed: Callable[[bool], None]
    apply_settings: ApplySettingsCallback
    apply_mapping: Callable[[GestureConfig], None]


class HandTrackingModule:
    key = "hand"
    name = "Hand tracking"
    description = "Live hand and gesture data, detection settings, and command mappings."

    def __init__(
        self, settings: Settings, actions: HandTrackingActions, *,
        model_asset: HandLandmarkerAsset | None = None,
    ) -> None:
        self.settings = settings
        self.actions = actions
        self.debug = HandDebugPanel(
            on_open_settings=self.open_settings, on_toggle_overlay=self.toggle_overlay,
            on_overlay_options=self.open_overlay_options,
        )
        self.settings_panel = HandSettingsPanel(on_apply=actions.apply_settings, model_asset=model_asset)
        # Mapping views capture criteria from live poses on demand.
        self.pose_feed = LivePoseFeed()
        self.mapping = MappingPanel(
            on_saved=actions.apply_mapping, segment_count=settings.data.finger_segment_count,
            pose_feed=self.pose_feed,
        )
        self.window: TrackingWindow | None = None
        self.overlay: HandTrackingOverlay | None = None
        self._debug_active = False

    def open(self, parent: tk.Misc) -> None:
        if self.overlay is None:
            self.overlay = HandTrackingOverlay(
                parent,
                max_deviation=self.settings.data.max_finger_deviation,
                preferences=self.settings.data.hand_overlay, on_save=self.save_overlay_preferences,
            )
            self._publish_report()
        if self.window is None:
            context = WindowContext(
                self.settings,
                ControlCallbacks(
                    on_restart=self.actions.restart, on_close=self.close,
                    on_apply=self.actions.apply_settings,
                    on_toggle_tracking=self.actions.toggle_pause,
                    on_main_active=self._set_debug_active,
                ),
                PanelSet(self.debug, self.settings_panel, self.mapping),
            )
            self.window = TrackingWindow(parent, context, self.name)
        self.window.show()

    @property
    def overlay_active(self) -> bool:
        return self.overlay is not None and self.overlay.enabled

    def _set_debug_active(self, active: bool) -> None:
        self._debug_active = active
        self._notify_activity()

    def open_overlay_options(self) -> None:
        if self.overlay is not None and self.debug.widget is not None:
            self.overlay.show_options(self.debug.widget.winfo_toplevel())

    def save_overlay_preferences(self, preferences: OverlaySettings) -> None:
        self.settings.update_fields({"hand_overlay": preferences})
        self.settings_panel.rebase(self.settings, ("hand_overlay",))

    def _notify_activity(self) -> None:
        self.actions.activity_changed(self._debug_active or self.overlay_active)

    def toggle_overlay(self) -> None:
        if self.overlay is None:
            return
        if self.overlay.enabled:
            self.overlay.close()
        else:
            try:
                self.overlay.enable()
            except (OSError, tk.TclError, RuntimeError) as error:
                assert self.debug.widget is not None
                messagebox.showerror(
                    "Could not enable overlay", str(error),
                    parent=self.debug.widget.winfo_toplevel(),
                )
                return
        self.debug.set_overlay_enabled(self.overlay.enabled)
        self._notify_activity()

    def open_settings(self) -> None:
        if self.window is not None:
            self.window.show_settings()

    @property
    def preview_active(self) -> bool:
        """Detection without commands, for the settings preview or a pose capture."""
        settings_preview = (
            self.window is not None and self.window.preview_visible
            and self.settings_panel.tracking_preview_active
        )
        return settings_preview or self.pose_feed.requested

    def _publish_report(self) -> None:
        """Show the debugging panel's current report on the desktop overlay."""
        if self.overlay is not None:
            self.overlay.update_data(self.debug.data)

    def update_data(self, records, enabled, paused):
        self.debug.update_gesture_display(records, enabled, paused)
        self._publish_report()
        self.settings_panel.set_preview_data(self.debug.preview_fingers, self.debug.preview_status)
        self.pose_feed.publish(records)

    def set_model_status(self, status):
        self.debug.set_model_status(status)
        self._publish_report()
        self.settings_panel.set_model_status(status)

    def synchronize(self, settings, changed_fields):
        max_deviation = settings.data.max_finger_deviation
        self.debug.set_display(settings.data.theme, max_deviation)
        if self.overlay is not None:
            self.overlay.set_display(max_deviation)
            if self.overlay.saved_preferences != settings.data.hand_overlay:
                self.overlay.load_preferences(settings.data.hand_overlay)
        if self.mapping.segment_count != settings.data.finger_segment_count:
            self.mapping.set_segment_count(settings.data.finger_segment_count)
        self.settings_panel.rebase(settings, changed_fields)

    def reload_settings(self, settings):
        self.settings_panel.show_settings(settings)
        self.synchronize(settings, ())

    def confirm_close(self) -> bool:
        return (
            (self.window is None or self.window.confirm_close())
            and (self.overlay is None or self.overlay.confirm_close())
        )

    def resize(self, scale: float) -> None:
        if self.window is not None:
            self.window.resize(scale)
        if self.overlay is not None:
            self.overlay.refresh()

    def close(self) -> None:
        try:
            if self.overlay is not None:
                self.overlay.shutdown()
        finally:
            self._debug_active = False
            if self.window is not None:
                self.window.close()
                self.window = None

    def hide_overlays(self) -> None:
        if self.overlay is not None:
            self.overlay.hide()
