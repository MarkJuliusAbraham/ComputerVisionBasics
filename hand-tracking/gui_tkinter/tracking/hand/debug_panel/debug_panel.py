"""Deferred hand debugging panel with cached live data."""

from dataclasses import replace
import tkinter as tk
from gui_tkinter.core.state import ControlCallbacks
from landmarker import ModelStatus
from settings.settings_manager import SettingsData

from .debug_tab import HandDebugTab
from .live_hand_data import LiveHandData


class HandDebugPanel:
    def __init__(self, on_open_settings=None):
        self.widget: HandDebugTab | None = None
        self._paused = False
        self.data = LiveHandData()
        self._model_status = ModelStatus()
        self._on_open_settings = on_open_settings

    def build(
        self, parent: tk.Misc, *, callbacks: ControlCallbacks,
        settings: SettingsData, camera_index: int = 0,
    ) -> HandDebugTab:
        self.widget = HandDebugTab(
            parent, on_restart=callbacks.on_restart, on_close=callbacks.on_close,
            on_toggle_tracking=callbacks.on_toggle_tracking,
            theme_name=settings.theme,
            max_deviation=settings.finger_classification_thresholds[-1],
            on_open_settings=self._on_open_settings,
        )
        self.widget.pack(fill="both", expand=True)
        self.set_tracking_paused(self._paused)
        self.set_model_status(self._model_status)
        return self.widget

    def set_tracking_paused(self, paused):
        self._paused = paused
        if self.widget is not None:
            self.widget.set_tracking_paused(paused)

    def set_model_status(self, status):
        self._model_status = status
        self.data = replace(self.data, blocking_reason=status.tracking_block_reason)
        if self.widget is not None:
            self.widget.model_status.set_status(status)
            self.widget.live_gestures.update_data(self.data)

    def update_gesture_display(self, hand_states, enabled=True, paused=False):
        self.data = LiveHandData(
            tuple(hand_states), enabled, paused, self._model_status.tracking_block_reason,
        )
        if self.widget is not None:
            self.widget.live_gestures.update_data(self.data)

    @property
    def preview_fingers(self):
        return self.data.preview_fingers

    @property
    def preview_status(self):
        return self.data.preview_status

    def set_display(self, theme_name, max_deviation):
        if self.widget is not None:
            self.widget.live_gestures.set_display(theme_name, max_deviation)
