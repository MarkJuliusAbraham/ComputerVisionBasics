"""Shared text presentation for detailed and compact hand reports."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from hand_tracking.backend.gestures.hand_report import HandReport

from .hand_summary_data import HandSummaryData


class HandSummary(ttk.Frame):
    def __init__(self, master: tk.Misc, *, row_padding: int = 4) -> None:
        super().__init__(master)
        self.variables = {
            name: tk.StringVar(self, value="—")
            for name in ("Status", "Palm", "Gesture", "Command")
        }
        self.columnconfigure(1, weight=1)
        for row, (name, variable) in enumerate(self.variables.items()):
            ttk.Label(self, text=name, width=9, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=row_padding,
            )
            ttk.Label(self, textvariable=variable, width=18, anchor="w").grid(
                row=row, column=1, sticky="ew", pady=row_padding,
            )
        self.set_data(None)

    def set_data(self, record: HandReport | None) -> None:
        for name, value in HandSummaryData.from_record(record).fields:
            variable = self.variables[name]
            if variable.get() != value:
                variable.set(value)
