"""Controls for the command sequence of the selected gesture."""

import tkinter as tk
from tkinter import ttk

from hand_tracking.frontend.components.theme import ThemeMetrics
from hand_tracking.frontend.core.change_notifications import ChangeNotifications
from hand_tracking.frontend.core.scaled_layout import ScaledLayout


class CommandSequenceSection(ttk.LabelFrame):
    """Keep editable key and delay text together, including incomplete values."""

    def __init__(self, master, on_change=None, appearance=None):
        super().__init__(master, text="Command sequence")
        self.appearance = appearance if appearance is not None else ThemeMetrics(self)
        self.changes = ChangeNotifications(self, on_change)
        self.commands = tk.StringVar(self)
        self.delay = tk.StringVar(self)

        self.layout = ScaledLayout(self, self.appearance)
        self.layout.configure(self, padding=16)
        ttk.Label(self, text="Keys", anchor="w").pack(anchor="w")
        self.layout.pack(ttk.Entry(self, textvariable=self.commands), fill="x", pady=(6, 0))
        ttk.Label(self, text="Enter one key per step, separated by commas.").pack(
            anchor="w", pady=(6, 12)
        )
        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Label(row, text="Delay between steps (ms)", anchor="w").pack(side="left")
        self.layout.pack(ttk.Spinbox(
            row, textvariable=self.delay, from_=0, to=10000, increment=50, width=10,
        ), side="right", padx=(12, 0))
        self.changes.watch(self.commands, self.delay)

    def load(self, commands, delay):
        with self.changes.suspended():
            self.commands.set(commands)
            self.delay.set(delay)
