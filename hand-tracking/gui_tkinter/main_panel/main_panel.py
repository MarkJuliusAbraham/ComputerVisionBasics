"""Deferred main hub panel."""

import tkinter as tk

from camera_status import CameraStatus

from gui_tkinter.core.state import ControlCallbacks
from gui_tkinter.tracking.registry import TrackingWindowRegistry
from settings.settings_manager import SettingsData

from .main_tab import MainTab


class MainPanel:
    def __init__(self, tracking_modules: TrackingWindowRegistry) -> None:
        self.tracking_modules = tracking_modules
        self.widget: MainTab | None = None

    def build(
        self, parent: tk.Misc, *, callbacks: ControlCallbacks,
        settings: SettingsData, camera_index: int = 0,
    ) -> MainTab:
        self.widget = MainTab(
            parent, self.tracking_modules, callbacks, camera_index=camera_index,
        )
        self.widget.pack(fill="both", expand=True)
        return self.widget

    def update_camera_state(self, status: CameraStatus) -> None:
        if self.widget is not None:
            self.widget.camera.update_state(status)
