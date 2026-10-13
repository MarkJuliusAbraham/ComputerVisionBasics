"""Controls for the command sequence of the selected gesture."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.theme import ThemeMetrics
from gui_tkinter.core.change_notifications import ChangeNotifications
from gui_tkinter.core.idle_refresh import IdleRefresh


class CommandSequenceSection(ttk.LabelFrame):
    """Keep editable key and delay text together, including incomplete values."""

    def __init__(self, master, on_change=None, appearance=None):
        super().__init__(master, text="Command sequence")
        self.appearance = appearance if appearance is not None else ThemeMetrics(self)
        self.changes = ChangeNotifications(self, on_change)
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
        self.changes.watch(self.commands, self.delay)
        self._refresh_layout()
        self.theme_refresh = IdleRefresh(self, self._refresh_layout, event="<<ThemeChanged>>")

    def _refresh_layout(self):
        self.appearance.refresh()
        self.configure(padding=self.appearance.pixels(16))

    def load(self, commands, delay):
        with self.changes.suspended():
            self.commands.set(commands)
            self.delay.set(delay)
