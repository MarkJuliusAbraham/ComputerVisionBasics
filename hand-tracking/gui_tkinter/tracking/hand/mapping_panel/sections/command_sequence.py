"""Controls for the command sequence of the selected gesture."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.theme import ThemeMetrics


class CommandSequenceSection(ttk.LabelFrame):
    """Keep editable key and delay text together, including incomplete values."""

    def __init__(self, master, on_change=None, appearance=None):
        super().__init__(master, text="Command sequence")
        self.appearance = appearance if appearance is not None else ThemeMetrics(self)
        self._on_change = on_change
        self._loading = False
        self.commands = tk.StringVar(self)
        self.delay = tk.StringVar(self)

        ttk.Label(self, text="Keys", anchor="w").pack(anchor="w")
        ttk.Entry(self, textvariable=self.commands).pack(
            fill="x", pady=(self.appearance.pixels(6), 0),
        )
        ttk.Label(self, text="Enter one key per step, separated by commas.").pack(
            anchor="w", pady=(6, 12)
        )
        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Label(row, text="Delay between steps (ms)", anchor="w").pack(side="left")
        ttk.Spinbox(
            row, textvariable=self.delay, from_=0, to=10000, increment=50, width=10,
        ).pack(side="right", padx=(self.appearance.pixels(12), 0))
        for variable in (self.commands, self.delay):
            variable.trace_add("write", self._changed)
        self._refresh_layout()
        self.bind("<<ThemeChanged>>", lambda _event: self._refresh_layout())

    def _refresh_layout(self):
        self.appearance.refresh()
        self.configure(padding=self.appearance.pixels(16))

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
