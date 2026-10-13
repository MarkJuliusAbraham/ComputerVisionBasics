"""Composition of hand tracking panels, independent of the hub's layout."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Callable

from gestures.gesture_config import GestureConfig
from gui_tkinter.core.callbacks import Action, ApplySettingsCallback
from gui_tkinter.core.state import ControlCallbacks, PanelSet, WindowContext
from gui_tkinter.tracking.window import TrackingWindow
from landmarker import HandLandmarkerAsset
from settings.settings_manager import Settings

from .debug_panel import HandDebugPanel
from .mapping_panel import MappingPanel
from .settings_panel import HandSettingsPanel


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
        self.debug = HandDebugPanel(on_open_settings=self.open_settings)
        self.settings_panel = HandSettingsPanel(on_apply=actions.apply_settings, model_asset=model_asset)
        self.mapping = MappingPanel(
            on_saved=actions.apply_mapping, segment_count=settings.data.finger_segment_count,
        )
        self.window: TrackingWindow | None = None

    def open(self, parent: tk.Misc) -> None:
        if self.window is None:
            context = WindowContext(
                self.settings,
                ControlCallbacks(
                    on_restart=self.actions.restart, on_close=self.close,
                    on_apply=self.actions.apply_settings,
                    on_toggle_tracking=self.actions.toggle_pause,
                    on_main_active=self.actions.activity_changed,
                ),
                PanelSet(self.debug, self.settings_panel, self.mapping),
            )
            self.window = TrackingWindow(parent, context, self.name)
        self.window.show()

    def open_settings(self) -> None:
        if self.window is not None:
            self.window.show_settings()

    @property
    def preview_active(self) -> bool:
        return (
            self.window is not None and self.window.preview_visible
            and self.settings_panel.tracking_preview_active
        )

    def update_data(self, records, enabled, paused):
        self.debug.update_gesture_display(records, enabled, paused)
        self.settings_panel.set_preview_data(self.debug.preview_fingers, self.debug.preview_status)

    def set_model_status(self, status):
        self.debug.set_model_status(status)
        self.settings_panel.set_model_status(status)

    def synchronize(self, settings, changed_fields):
        self.debug.set_display(settings.data.theme, settings.data.finger_classification_thresholds[-1])
        if self.mapping.segment_count != settings.data.finger_segment_count:
            self.mapping.set_segment_count(settings.data.finger_segment_count)
        self.settings_panel.rebase(settings, changed_fields)

    def reload_settings(self, settings):
        self.settings_panel.show_settings(settings)
        self.synchronize(settings, ())

    def confirm_close(self) -> bool:
        return self.window is None or self.window.confirm_close()

    def resize(self, scale: float) -> None:
        if self.window is not None:
            self.window.resize(scale)

    def close(self) -> None:
        if self.window is not None:
            self.window.close()
            self.window = None
