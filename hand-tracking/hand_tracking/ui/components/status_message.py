"""A fixed-height, wrapping status message with semantic theme colors."""

import tkinter as tk
from tkinter import ttk
from hand_tracking.ui.core.idle_refresh import IdleRefresh

from .theme import ThemeMetrics


class StatusMessage(ttk.Frame):
    def __init__(self, master, *, lines=2, appearance=None):
        super().__init__(master)
        self.appearance = appearance if appearance is not None else ThemeMetrics(self)
        self.lines = lines
        self._warning = False
        self.text = tk.StringVar(self)
        self.pack_propagate(False)
        self.label = ttk.Label(
            self, textvariable=self.text, width=1, anchor="nw", justify="left",
        )
        self.label.pack(fill="both", expand=True)
        self.bind("<Configure>", self._resize)
        self.theme_refresh = IdleRefresh(self, self._refresh_theme, event="<<ThemeChanged>>")
        self._refresh_theme()

    def set(self, message, *, warning=False):
        self.text.set(message)
        self._warning = warning
        self._refresh_theme()

    def use_variable(self, variable):
        """Display an existing form status source without copying its state."""
        self.text = variable
        self.label.configure(textvariable=variable)

    def _refresh_theme(self):
        self.appearance.refresh()
        self.configure(height=self.lines * self.appearance.font.metrics("linespace"))
        self.label.configure(
            foreground=self.appearance.colors.high_alert.foreground if self._warning
            else self.appearance.colors.palette.muted,
        )

    def _resize(self, event):
        self.label.configure(wraplength=max(event.width, 1))
