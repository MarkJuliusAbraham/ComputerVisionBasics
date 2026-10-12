"""Selected gesture name and a stable, theme-aware conflict warning."""

import tkinter as tk
from tkinter import ttk


class GestureHeading(ttk.Frame):
    def __init__(self, master, appearance):
        super().__init__(master)
        self.appearance = appearance
        self.name = tk.StringVar(self)
        self.warning = tk.StringVar(self)
        self.columnconfigure(0, weight=1)
        ttk.Label(
            self, textvariable=self.name, font=appearance.heading_font, width=1, anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        self.warning_area = ttk.Frame(self)
        self.warning_area.grid(row=1, column=0, sticky="ew")
        self.warning_area.pack_propagate(False)
        self.warning_label = ttk.Label(
            self.warning_area, textvariable=self.warning, width=1, anchor="nw", justify="left",
        )
        self.warning_label.pack(fill="both", expand=True)
        self.warning_area.bind("<Configure>", self._resize_warning)
        self.bind("<<ThemeChanged>>", lambda _event: self.after_idle(self._refresh_theme))
        self._refresh_theme()

    def _refresh_theme(self):
        self.appearance.refresh()
        self.warning_area.configure(height=2 * self.appearance.font.metrics("linespace"))
        self.warning_area.grid_configure(pady=(self.appearance.pixels(6), 0))
        self.warning_label.configure(foreground=self.appearance.colors.high_alert.foreground)

    def _resize_warning(self, event):
        self.warning_label.configure(wraplength=max(event.width, 1))

    def show_conflict(self, conflict, names):
        message = "Conflict: " + conflict.description(names, maximum_names=1) if conflict else ""
        if self.warning.get() != message:
            self.warning.set(message)
