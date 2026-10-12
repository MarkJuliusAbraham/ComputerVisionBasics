"""Editable deviation ranges and a live preview of their classification."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.finger_threshold_control import FingerThresholdControl
from gui_tkinter.components.theme import ThemeMetrics
from settings.settings_manager import default_finger_thresholds, resize_finger_thresholds

from .deviation_preview import DeviationPreview


class DeviationSettings(ttk.Frame):
    """Keep segment count, split points, and their preview synchronized."""

    def __init__(self, master, theme_name, max_deviation, on_change=None):
        super().__init__(master)
        self._on_change = on_change
        self._loading = False
        self.appearance = ThemeMetrics(self)
        self.segment_count = tk.IntVar(self, value=4)
        self.variables = {"finger_segment_count": self.segment_count}

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(12, 4))
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header, text="Finger deviation ranges", font=self.appearance.heading_font,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Segments").grid(row=0, column=1, padx=(12, 8))
        self.segment_control = ttk.Spinbox(
            header, textvariable=self.segment_count, values=(4, 5, 6),
            from_=4, to=6, increment=1, state="readonly", width=4, wrap=False,
        )
        self.segment_control.grid(row=0, column=2, sticky="e")

        self.control = FingerThresholdControl(
            self, thresholds=default_finger_thresholds(4), segment_count=4,
            on_change=self._thresholds_changed,
        )
        self.control.pack(fill="x", pady=(0, 6))
        self.preview = DeviationPreview(
            self, theme_name=theme_name, max_deviation=max_deviation,
        )
        self.preview.pack(fill="x")
        self.segment_count.trace_add("write", self._segments_changed)
        self.bind("<<ThemeChanged>>", lambda _event: self.appearance.refresh())
        self.set_theme(theme_name)
        self._update_preview()

    def _segments_changed(self, *_args):
        if self._loading:
            return
        count = self.segment_count.get()
        thresholds = resize_finger_thresholds(self.control.thresholds, count)
        self.control.set_ranges(thresholds, count)
        self._thresholds_changed()

    def _thresholds_changed(self):
        self._update_preview()
        if not self._loading and self._on_change:
            self._on_change()

    def _update_preview(self):
        thresholds = self.control.thresholds
        self.preview.set_thresholds(
            thresholds, self.segment_count.get(), thresholds[-1],
        )

    def values(self):
        return {
            "finger_segment_count": self.segment_count.get(),
            "finger_classification_thresholds": self.control.thresholds,
        }

    def load(self, data):
        self._loading = True
        try:
            self.segment_count.set(data.finger_segment_count)
            self.control.set_ranges(
                data.finger_classification_thresholds, data.finger_segment_count,
            )
            self._update_preview()
        finally:
            self._loading = False

    def set_theme(self, theme_name):
        self.control.set_theme(theme_name)
        self.preview.set_theme(theme_name)
