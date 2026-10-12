"""Controls for the command sequence of the selected gesture."""

import tkinter as tk
from tkinter import ttk


class CommandSequenceSection(ttk.LabelFrame):
    """Keep editable key and delay text together, including incomplete values."""

    def __init__(self, master, on_change=None):
        super().__init__(master, text="Command Sequence", padding=14)
        self._on_change = on_change
        self._loading = False
        self.commands = tk.StringVar(self)
        self.delay = tk.StringVar(self)

        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Label(row, text="Keys", width=18, anchor="w").pack(side="left")
        ttk.Entry(row, textvariable=self.commands).pack(side="left", fill="x", expand=True)
        ttk.Label(self, text="Enter one key per step, separated by commas.").pack(
            anchor="w", pady=(6, 12)
        )
        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Label(row, text="Delay between steps (ms)", width=24, anchor="w").pack(side="left")
        ttk.Spinbox(
            row, textvariable=self.delay, from_=0, to=10000, increment=50, width=10,
        ).pack(side="left")
        for variable in (self.commands, self.delay):
            variable.trace_add("write", self._changed)

    def load(self, commands, delay):
        self._loading = True
        try:
            self.commands.set(commands)
            self.delay.set(delay)
        finally:
            self._loading = False

    def _changed(self, *_args):
        if not self._loading and self._on_change:
            self._on_change()
