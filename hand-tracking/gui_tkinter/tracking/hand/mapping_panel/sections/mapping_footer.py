"""Persistent mapping commit actions with a stable status area."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.buttons import DiscardChangesButton


class MappingFooter(ttk.Frame):
    def __init__(self, master, appearance, on_save=None, on_discard=None):
        super().__init__(master)
        self.appearance = appearance
        self.status = tk.StringVar(self, value="Gesture mappings loaded")
        self.save_button = ttk.Button(
            self, text="Save mappings", command=on_save, style="Accent.TButton",
        )
        self.save_button.pack(side="right")
        self.discard_button = DiscardChangesButton(self, command=on_discard)
        self.discard_button.pack(side="right", padx=(0, appearance.pixels(10)))
        self.status_area = ttk.Frame(self)
        self.status_area.pack(side="left", fill="x", expand=True, padx=(0, appearance.pixels(12)))
        self.status_area.pack_propagate(False)
        self.label = ttk.Label(self.status_area, textvariable=self.status, anchor="w", width=1)
        self.label.pack(fill="both", expand=True)
        self.status_area.bind("<Configure>", self._resize_status)
        self.bind("<<ThemeChanged>>", lambda _event: self._reserve_height())
        self._reserve_height()

    def _reserve_height(self):
        self.appearance.refresh()
        self.status_area.configure(height=2 * self.appearance.font.metrics("linespace"))

    def _resize_status(self, event):
        self.label.configure(wraplength=max(event.width, 1))

    def set_dirty(self, dirty):
        state = ["!disabled"] if dirty else ["disabled"]
        self.save_button.state(state)
        self.discard_button.state(state)

    def set_status(self, message):
        self.status.set(message)
