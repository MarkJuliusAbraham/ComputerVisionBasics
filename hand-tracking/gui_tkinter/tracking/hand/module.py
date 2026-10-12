"""Composition of hand tracking panels, independent of the hub's layout."""

from dataclasses import dataclass
from typing import Callable

from gui_tkinter.core.state import ControlCallbacks, ControlWindowContext, PanelSet
from gui_tkinter.tracking.window import TrackingWindow

from .debug_panel import HandDebugPanel
from .mapping_panel import MappingPanel
from .settings_panel import HandSettingsPanel


@dataclass(frozen=True)
class HandTrackingActions:
    restart: Callable
    toggle_pause: Callable
    activity_changed: Callable
    apply_settings: Callable
    apply_mapping: Callable


class HandTrackingModule:
    key = "hand"
    name = "Hand tracking"
    description = "Live hand and gesture data, detection settings, and command mappings."

    def __init__(self, settings, actions):
        self.settings = settings
        self.actions = actions
        self.debug = HandDebugPanel()
        self.settings_panel = HandSettingsPanel(on_apply=actions.apply_settings)
        self.mapping = MappingPanel(
            on_saved=actions.apply_mapping, segment_count=settings.data.finger_segment_count,
        )
        self.window = None

    def open(self, parent):
        if self.window is None:
            context = ControlWindowContext(
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

    @property
    def preview_active(self):
        return (
            self.window is not None and self.window.preview_visible
            and self.settings_panel.tracking_preview_active
        )

    def update_data(self, records, enabled, paused):
        self.debug.update_gesture_display(records, enabled, paused)
        self.settings_panel.set_preview_data(self.debug.preview_fingers, self.debug.preview_status)

    def synchronize(self, settings, changed_fields):
        self.debug.set_display(settings.data.theme, settings.data.finger_classification_thresholds[-1])
        if self.mapping.segment_count != settings.data.finger_segment_count:
            self.mapping.set_segment_count(settings.data.finger_segment_count)
        self.settings_panel.rebase(settings, changed_fields)

    def reload_settings(self, settings):
        self.settings_panel.show_settings(settings)
        self.synchronize(settings, ())

    def confirm_close(self):
        return self.window is None or self.window.confirm_close()

    def resize(self, scale):
        if self.window is not None:
            self.window.resize(scale)

    def close(self):
        if self.window is not None:
            self.window.close()
            self.window = None
