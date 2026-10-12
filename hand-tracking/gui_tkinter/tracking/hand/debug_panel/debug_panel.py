"""Deferred hand debugging panel with cached live data."""

from .debug_tab import HandDebugTab


class HandDebugPanel:
    def __init__(self):
        self.widget = None
        self._paused = False
        self._report_paused = False
        self._records = []
        self._enabled = True

    def build(self, parent, *, callbacks, settings, camera_index=0):
        self.widget = HandDebugTab(
            parent, on_restart=callbacks.on_restart, on_close=callbacks.on_close,
            on_toggle_tracking=callbacks.on_toggle_tracking,
            theme_name=settings.theme,
            max_deviation=settings.finger_classification_thresholds[-1],
        )
        self.widget.pack(fill="both", expand=True)
        self.set_tracking_paused(self._paused)
        self.update_gesture_display(self._records, self._enabled, self._report_paused)
        return self.widget

    def set_tracking_paused(self, paused):
        self._paused = paused
        if self.widget is not None:
            self.widget.set_tracking_paused(paused)

    def update_gesture_display(self, hand_states, enabled=True, paused=False):
        self._records = list(hand_states)
        self._enabled = enabled
        self._report_paused = paused
        if self.widget is not None:
            self.widget.live_gestures.update_data(hand_states, enabled=enabled, paused=paused)

    @property
    def preview_fingers(self):
        return self._records[0]["state"].fingers if self._records else None

    @property
    def preview_status(self):
        if not self._enabled:
            return "Tracking disabled"
        if self._report_paused:
            return "Tracking paused"
        if not self._records:
            return "No hand detected"
        return f"Live data · {self._records[0]['handedness']} hand"

    def set_display(self, theme_name, max_deviation):
        if self.widget is not None:
            self.widget.live_gestures.set_display(theme_name, max_deviation)
