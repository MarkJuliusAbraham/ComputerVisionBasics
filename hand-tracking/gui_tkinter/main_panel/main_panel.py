"""Deferred main hub panel."""

from .main_tab import MainTab


class MainPanel:
    def __init__(self, tracking_modules):
        self.tracking_modules = tracking_modules
        self.widget = None

    def build(self, parent, *, callbacks, settings, camera_index=0):
        self.widget = MainTab(
            parent, self.tracking_modules, callbacks, camera_index=camera_index,
        )
        self.widget.pack(fill="both", expand=True)
        return self.widget

    def update_camera_state(self, state, requested, active, message=None):
        if self.widget is not None:
            self.widget.camera.update_state(state, requested, active, message)
