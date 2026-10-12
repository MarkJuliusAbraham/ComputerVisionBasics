from .main_tab import MainTab


class MainPanel:
    """Deferred main-page panel used by ControlWindow."""

    def __init__(self):
        self.widget = None

    def build(self, parent, *, on_restart, on_close, camera_index=0,
              on_camera_switch=None, on_toggle_tracking=None,
              theme_name="Light", max_deviation=75.0):
        self.widget = MainTab(
            parent,
            on_restart=on_restart,
            on_close=on_close,
            camera_index=camera_index,
            on_camera_switch=on_camera_switch,
            on_toggle_tracking=on_toggle_tracking,
            theme_name=theme_name,
            max_deviation=max_deviation,
        )
        self.widget.pack(fill="both", expand=True)
        return self.widget

    def switch_camera(self):
        if self.widget is not None:
            self.widget.switch_camera()

    def set_tracking_paused(self, paused):
        if self.widget is not None:
            self.widget.set_tracking_paused(paused)

    def update_camera_state(self, state, requested, active, message=None):
        if self.widget is not None:
            self.widget.update_camera_state(state, requested, active, message)

    def update_gesture_display(self, hand_states, enabled=True, paused=False):
        if self.widget is not None:
            self.widget.update_gesture_display(
                hand_states, enabled=enabled, paused=paused
            )

    @property
    def preview_fingers(self):
        return self.widget.preview_fingers if self.widget is not None else None

    @property
    def preview_status(self):
        return self.widget.preview_status if self.widget is not None else "No hand detected"

    def set_display(self, theme_name, max_deviation):
        if self.widget is not None:
            self.widget.set_display(theme_name, max_deviation)
