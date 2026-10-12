"""Interactive deviation preview used by the tracking settings section."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.deviation_bar import DeviationBar
from gestures.finger_classifier import FingerClassifier, FingerState, finger_categories


class DeviationPreview(ttk.Frame):
    """Show live finger deviations using the currently edited thresholds."""

    def __init__(self, master, theme_name="Light", max_deviation=75.0):
        super().__init__(master)
        self._visible = False
        self._theme_name = theme_name
        self._max_deviation = max_deviation
        self._thresholds = (15.0, 45.0, 75.0)
        self._segment_count = 4
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
            self, theme_name=theme_name, max_deviation=max_deviation
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

    def set_thresholds(self, thresholds, segment_count, max_deviation=None):
        self._thresholds = tuple(float(value) for value in thresholds)
        self._segment_count = segment_count
        if max_deviation is not None:
            self._max_deviation = max_deviation
        if self._visible:
            self._render()

    def _render(self):
        categories = finger_categories(self._segment_count)
        fingers = {}
        for name, finger in (self._latest_fingers or {}).items():
            position = FingerClassifier.classify_deviation(
                finger.deviation, self._thresholds, categories
            )
            fingers[name] = FingerState(finger.deviation, position, finger.tip)

        self.status.set(self._latest_status)
        self.bar.set_data(
            fingers or None,
            self._theme_name,
            self._max_deviation,
        )
