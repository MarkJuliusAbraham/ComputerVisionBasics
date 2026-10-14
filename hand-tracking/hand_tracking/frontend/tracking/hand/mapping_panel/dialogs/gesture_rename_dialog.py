"""A focused name editor that commits through injected gesture management."""

import tkinter as tk
from tkinter import ttk

from hand_tracking.frontend.components.theme import ThemeMetrics
from hand_tracking.frontend.core.modal_dialog import ModalDialog


class GestureRenameDialog:
    def __init__(self, parent, name, on_save):
        self.parent = parent
        self.name = name
        self.on_save = on_save

    def show(self):
        self.modal = ModalDialog(self.parent, "Rename gesture", base_size=(480, 220))
        self.window = self.modal.window
        appearance = ThemeMetrics(self.window)
        footer = ttk.Frame(self.window, padding=appearance.pixels(16))
        footer.pack(side="bottom", fill="x")
        ttk.Button(footer, text="Save name", command=self._save,
                   style="Accent.TButton").pack(side="right")
        ttk.Button(footer, text="Cancel", command=self.window.destroy).pack(
            side="right", padx=(0, appearance.pixels(8)),
        )
        body = ttk.Frame(self.window, padding=appearance.pixels(16))
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Gesture name").pack(anchor="w")
        self.name_var = tk.StringVar(self.window, value=self.name)
        self.entry = ttk.Entry(body, textvariable=self.name_var)
        self.entry.pack(fill="x", pady=(appearance.pixels(8), 0))
        self.error_var = tk.StringVar(self.window)
        ttk.Label(
            body, textvariable=self.error_var, wraplength=appearance.pixels(448),
            justify="left",
        ).pack(anchor="w", pady=(appearance.pixels(8), 0))
        self.window.bind("<Return>", lambda _event: self._save())
        self.entry.selection_range(0, "end")
        self.modal.show(scale=appearance.scale, initial_focus=self.entry)

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            self.error_var.set("Enter a gesture name.")
            self.entry.focus_set()
            return
        if name != self.name:
            try:
                self.on_save(name)
            except (OSError, ValueError) as error:
                self.error_var.set(f"Could not rename gesture: {error}")
                return
        self.window.destroy()
