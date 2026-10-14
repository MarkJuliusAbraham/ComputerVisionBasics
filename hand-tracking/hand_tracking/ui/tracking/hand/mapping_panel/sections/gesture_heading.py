"""Selected gesture name and a stable, theme-aware conflict warning."""

from hand_tracking.ui.core.idle_refresh import IdleRefresh
import tkinter as tk
from tkinter import ttk
from hand_tracking.ui.components.status_message import StatusMessage


class GestureHeading(ttk.Frame):
    def __init__(self, master, appearance):
        super().__init__(master)
        self.appearance = appearance
        self.name = tk.StringVar(self)
        self.columnconfigure(0, weight=1)
        ttk.Label(
            self, textvariable=self.name, font=appearance.heading_font, width=1, anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        self.warning_area = StatusMessage(self, appearance=appearance)
        self.warning_area.grid(row=1, column=0, sticky="ew")
        self.theme_refresh = IdleRefresh(self, self._refresh_theme, event="<<ThemeChanged>>")
        self._refresh_theme()

    def _refresh_theme(self):
        self.appearance.refresh()
        self.warning_area.grid_configure(pady=(self.appearance.pixels(6), 0))

    def show_conflict(self, conflict, names):
        message = "Conflict: " + conflict.description(names, maximum_names=1) if conflict else ""
        if self.warning_area.text.get() != message:
            self.warning_area.set(message, warning=True)
