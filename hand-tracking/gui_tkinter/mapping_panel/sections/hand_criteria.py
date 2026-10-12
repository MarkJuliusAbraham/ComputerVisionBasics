"""Palm orientation and finger criteria as a single editing component."""

import tkinter as tk
from tkinter import ttk

from gestures.gesture_config import GestureMatch

from .criteria_options import PALM_OPTIONS
from .finger_criteria import FingerCriteriaEditor


class HandCriteriaSection(ttk.LabelFrame):
    """Expose one GestureMatch value instead of individual Tk variables."""

    def __init__(self, master, on_change=None):
        super().__init__(master, text="Hand Criteria", padding=12)
        self._on_change = on_change
        self._loading = False
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 12))
        palm_row = ttk.Frame(header)
        palm_row.pack(side="left", anchor="nw")
        ttk.Label(palm_row, text="Palm orientation", width=18, anchor="w").pack(side="left")
        self.palm = tk.StringVar(self, value="Any")
        ttk.Combobox(
            palm_row, textvariable=self.palm, values=tuple(PALM_OPTIONS),
            state="readonly", width=22,
        ).pack(side="left")
        self.mode_button = ttk.Button(
            header, text="Use classification checkboxes", width=30,
            command=self._toggle_mode,
        )
        self.mode_button.pack(side="right", anchor="ne")
        self.fingers = FingerCriteriaEditor(self, on_change=self._changed)
        self.fingers.pack(fill="x")
        self.palm.trace_add("write", self._changed)

    def values(self):
        return GestureMatch(
            palm=PALM_OPTIONS[self.palm.get()],
            fingers={name: choices for name, choices in self.fingers.values().items() if choices},
        )

    def load(self, match):
        self._loading = True
        try:
            self.palm.set(next(label for label, value in PALM_OPTIONS.items() if value == match.palm))
            self.fingers.load(match.fingers)
        finally:
            self._loading = False

    def _changed(self, *_args):
        if not self._loading and self._on_change:
            self._on_change()

    def _toggle_mode(self):
        self.fingers.toggle_mode()
        self.mode_button.configure(text=(
            "Use classification checkboxes" if self.fingers.mode == "straightness"
            else "Use straightness controls"
        ))
