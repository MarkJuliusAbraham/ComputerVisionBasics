"""Palm orientation and finger criteria as a single editing component."""

import tkinter as tk
from tkinter import ttk

from gestures.gesture_config import GestureMatch
from gui_tkinter.components.theme import ThemeMetrics

from .criteria_options import PALM_OPTIONS
from .finger_criteria import FingerCriteriaEditor


class HandCriteriaSection(ttk.Frame):
    """Group hand criteria under a heading, exposing one GestureMatch value."""

    def __init__(
        self, master, on_change=None, appearance=None, segment_count=4, show_heading=True,
    ):
        super().__init__(master)
        self.appearance = appearance or ThemeMetrics(self)
        self._on_change = on_change
        self._loading = False
        self.columnconfigure(0, weight=1)

        self.header = ttk.Frame(self)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(0, weight=1)
        if show_heading:
            ttk.Label(self.header, text="Hand criteria",
                      font=self.appearance.heading_font).grid(row=0, column=0, sticky="w")
        self.mode_button = ttk.Button(
            self.header, text="Use checklist", width=18, command=self._toggle_mode,
        )
        self.mode_button.grid(row=0, column=1, sticky="e")

        self.palm_row = ttk.Frame(self)
        self.palm_row.grid(row=1, column=0, sticky="ew")
        self.palm_row.columnconfigure(1, weight=1)
        ttk.Label(self.palm_row, text="Palm orientation", anchor="w").grid(
            row=0, column=0, sticky="w"
        )
        self.palm = tk.StringVar(self, value="Any")
        ttk.Combobox(
            self.palm_row, textvariable=self.palm, values=tuple(PALM_OPTIONS),
            state="readonly", width=1,
        ).grid(row=0, column=1, sticky="ew")

        self.fingers = FingerCriteriaEditor(
            self, on_change=self._changed, appearance=self.appearance,
            segment_count=segment_count,
        )
        self.fingers.grid(row=2, column=0, sticky="ew")
        self.mode_hint = tk.StringVar(
            self, value="Any position leaves that finger unrestricted.",
        )
        self.hint_label = ttk.Label(
            self, textvariable=self.mode_hint, width=1, anchor="w",
        )
        self.hint_label.grid(row=3, column=0, sticky="ew")
        self.availability_hint = ttk.Label(
            self, textvariable=self.fingers.availability_message, width=1, anchor="w",
        )
        self.availability_hint.grid(row=4, column=0, sticky="ew")
        self.palm.trace_add("write", self._changed)
        self._refresh_layout()
        self.bind("<<ThemeChanged>>", lambda _event: self.after_idle(self._refresh_layout))

    def _refresh_layout(self):
        self.appearance.refresh()
        gap = self.appearance.pixels(12)
        self.header.grid_configure(pady=(0, gap))
        self.palm_row.grid_configure(pady=(0, gap))
        self.palm_row.columnconfigure(0, minsize=self.fingers.label_width)
        self.hint_label.grid_configure(pady=(self.appearance.pixels(8), 0))
        self.availability_hint.grid_configure(pady=(self.appearance.pixels(6), 0))

    def set_segment_count(self, segment_count):
        self.fingers.set_segment_count(segment_count)

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
        checklist = self.fingers.mode == "classifications"
        self.mode_button.configure(text="Use simple choices" if checklist else "Use checklist")
        self.mode_hint.set(
            "A row with no checks accepts any position." if checklist else
            "Any position leaves that finger unrestricted."
        )
