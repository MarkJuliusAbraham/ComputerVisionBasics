"""Interactive deviation preview used by the tracking settings section."""

from dataclasses import replace
import tkinter as tk
from tkinter import ttk

from gestures.finger_thresholds import FingerThresholds
from gui_tkinter.components.deviation_bar import DeviationBar


class DeviationPreview(ttk.Frame):
    """Show live finger deviations using the currently edited thresholds."""

    def __init__(
        self, master, theme_name="Light", max_deviation=75.0,
        appearance=None, palette_provider=None,
    ):
        super().__init__(master)
        self._visible = False
        self._theme_name = theme_name
        self._max_deviation = max_deviation
        self._thresholds = FingerThresholds.defaults()
        self._latest_fingers = None
        self._latest_status = "No hand detected"

        self.button = ttk.Button(
            self, text="Test deviation", command=self.toggle
        )
        self.button.pack(anchor="w", pady=(2, 6))

        self.status = tk.StringVar(value=self._latest_status)
        self.status_label = ttk.Label(self, textvariable=self.status)
        self.status_label.pack(anchor="w", pady=(0, 2))

        self.bar = DeviationBar(
            self, theme_name=theme_name, max_deviation=max_deviation,
            appearance=appearance, palette_provider=palette_provider,
        )
        self.bar.pack(fill="x", pady=(0, 6))
        self.status_label.pack_forget()
        self.bar.pack_forget()

    @property
    def visible(self):
        return self._visible

    def toggle(self):
        self._visible = not self._visible
        if self._visible:
            self.status_label.pack(anchor="w", pady=(0, 2))
            self.bar.pack(fill="x", pady=(0, 6))
            self.button.configure(text="Hide test")
            self._render()
        else:
            self.bar.pack_forget()
            self.status_label.pack_forget()
            self.button.configure(text="Test deviation")

    def set_theme(self, theme_name):
        self._theme_name = theme_name
        self.bar.set_theme(theme_name)

    def set_data(self, fingers, status):
        self._latest_fingers = fingers
        self._latest_status = status
        if self._visible:
            self._render()

    def set_thresholds(self, thresholds: FingerThresholds):
        """Classify with the edited ranges; the last split sets the bar scale."""
        self._thresholds = thresholds
        self._max_deviation = thresholds.max_deviation
        if self._visible:
            self._render()

    def _render(self):
        fingers = {
            name: replace(finger, position=self._thresholds.classify(finger.deviation))
            for name, finger in (self._latest_fingers or {}).items()
        }

        self.status.set(self._latest_status)
        self.bar.set_data(
            fingers or None,
            self._theme_name,
            self._max_deviation,
        )
