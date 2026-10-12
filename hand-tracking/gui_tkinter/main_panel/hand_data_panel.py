"""Readable live summary and finger deviations for one hand."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.deviation_bar import DeviationBar


class HandDataPanel(ttk.LabelFrame):
    """Keep hand summary fields and the five finger rows together."""

    def __init__(self, master, handedness, theme_name="Light", max_deviation=75.0):
        super().__init__(master, text=f"{handedness} hand", padding=(14, 12))
        self._theme_name = theme_name
        self._max_deviation = max_deviation
        self._record = None

        self.detection = tk.StringVar(self, value="Not detected")
        self.palm = tk.StringVar(self, value="—")
        self.gesture = tk.StringVar(self, value="—")
        self.command = tk.StringVar(self, value="—")
        summary = ttk.Frame(self)
        summary.pack(fill="x")
        summary.columnconfigure(1, weight=1)
        for row, (label, variable) in enumerate((
            ("Status", self.detection),
            ("Palm", self.palm),
            ("Gesture", self.gesture),
            ("Command", self.command),
        )):
            ttk.Label(summary, text=label, width=9, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=4
            )
            ttk.Label(summary, textvariable=variable, width=18, anchor="w").grid(
                row=row, column=1, sticky="ew", pady=4
            )

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(12, 14))
        self.deviations = DeviationBar(
            self, theme_name=theme_name, max_deviation=max_deviation,
        )
        self.deviations.pack(fill="x")

    def set_data(self, record):
        self._record = record
        if record is None:
            self.detection.set("Not detected")
            self.palm.set("—")
            self.gesture.set("—")
            self.command.set("—")
            fingers = None
        else:
            self.detection.set("Detected")
            self.palm.set(record["state"].palm.value.replace("_", " ").title())
            gesture = record["gesture"]
            self.gesture.set(gesture.name if gesture else "—")
            self.command.set(
                self._describe_commands(gesture.commands) if gesture else "—"
            )
            fingers = record["state"].fingers
        self.deviations.set_data(fingers, self._theme_name, self._max_deviation)

    @staticmethod
    def _describe_commands(sequence):
        key_names = {" ": "Space", "\t": "Tab", "\n": "Enter", "\r": "Enter"}
        return " → ".join(
            key_names.get(step.value, step.value) for step in sequence.steps
        )

    def set_display(self, theme_name, max_deviation):
        self._theme_name = theme_name
        self._max_deviation = max_deviation
        self.set_data(self._record)
