"""Palm orientation and finger criteria as a single editing component."""

import tkinter as tk
from tkinter import ttk

from gestures.gesture_config import GestureMatch
from gui_tkinter.components.theme import ThemeMetrics
from gui_tkinter.core.change_notifications import ChangeNotifications
from gui_tkinter.core.scaled_layout import ScaledLayout

from .criteria_options import PALM_OPTIONS

PALM_LABELS = {value: label for label, value in PALM_OPTIONS.items()}
from .finger_criteria import FingerCriteriaEditor


class HandCriteriaSection(ttk.Frame):
    """Group hand criteria under a heading, exposing one GestureMatch value."""

    def __init__(
        self, master, on_change=None, appearance=None, segment_count=4, show_heading=True,
    ):
        super().__init__(master)
        self.appearance = appearance or ThemeMetrics(self)
        self.changes = ChangeNotifications(self, on_change)
        self.columnconfigure(0, weight=1)
        self.layout = ScaledLayout(self, self.appearance, on_refresh=self._size_label_column)

        self.header = self.layout.grid(ttk.Frame(self), row=0, column=0, sticky="ew", pady=(0, 12))
        self.header.columnconfigure(0, weight=1)
        if show_heading:
            ttk.Label(self.header, text="Hand criteria",
                      font=self.appearance.heading_font).grid(row=0, column=0, sticky="w")
        self.mode_button = ttk.Button(
            self.header, text="Use checklist", width=18, command=self._toggle_mode,
        )
        self.mode_button.grid(row=0, column=1, sticky="e")

        self.palm_row = self.layout.grid(ttk.Frame(self), row=1, column=0, sticky="ew", pady=(0, 12))
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
            self, on_change=self.changes.emit, appearance=self.appearance,
            segment_count=segment_count,
        )
        self.fingers.grid(row=2, column=0, sticky="ew")
        self.mode_hint = tk.StringVar(
            self, value="Any position leaves that finger unrestricted.",
        )
        self.hint_label = self.layout.grid(ttk.Label(
            self, textvariable=self.mode_hint, width=1, anchor="w",
        ), row=3, column=0, sticky="ew", pady=(8, 0))
        self.availability_hint = self.layout.grid(ttk.Label(
            self, textvariable=self.fingers.availability_message, width=1, anchor="w",
        ), row=4, column=0, sticky="ew", pady=(6, 0))
        self.changes.watch(self.palm)
        self._size_label_column()

    def _size_label_column(self):
        # Align the palm label with the finger tables' label column.
        self.palm_row.columnconfigure(0, minsize=self.fingers.label_width)

    def set_segment_count(self, segment_count):
        self.fingers.set_segment_count(segment_count)

    def values(self):
        return GestureMatch(
            palm=PALM_OPTIONS[self.palm.get()],
            fingers={name: choices for name, choices in self.fingers.values().items() if choices},
        )

    def load(self, match):
        with self.changes.suspended():
            self.palm.set(PALM_LABELS[match.palm])
            self.fingers.load(match.fingers)

    def _toggle_mode(self):
        self.fingers.toggle_mode()
        checklist = self.fingers.mode == "classifications"
        self.mode_button.configure(text="Use simple choices" if checklist else "Use checklist")
        self.mode_hint.set(
            "A row with no checks accepts any position." if checklist else
            "Any position leaves that finger unrestricted."
        )
