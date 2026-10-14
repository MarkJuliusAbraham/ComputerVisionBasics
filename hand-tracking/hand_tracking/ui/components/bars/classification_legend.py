"""A stable legend that keeps every classification visible, even narrow bands."""

import tkinter as tk
from tkinter import ttk


class ClassificationLegend(ttk.Frame):
    def __init__(self, master, appearance):
        super().__init__(master)
        self.appearance = appearance
        self._entries = []
        self._signature = None

    def display(self, categories, palette):
        signature = (tuple(categories), palette, self.appearance.scale)
        if signature == self._signature:
            return
        for entry in self._entries:
            entry.destroy()
        for column in range(len(self._entries)):
            self.columnconfigure(column, weight=0, minsize=0, uniform="")
        self._entries.clear()
        pixels = self.appearance.pixels
        for column, category in enumerate(categories):
            self.columnconfigure(column, weight=1, uniform="classification")
            entry = ttk.Frame(self)
            entry.grid(row=0, column=column, sticky="ew", padx=pixels(3))
            entry.columnconfigure(0, weight=1)
            dot = tk.Canvas(
                entry, width=pixels(12), height=pixels(10),
                background=palette.surface, highlightthickness=0, borderwidth=0,
            )
            dot.grid(row=0, column=0, pady=(0, pixels(4)))
            dot.create_oval(
                pixels(3), pixels(2), pixels(9), pixels(8),
                fill=palette.classification(category), outline="",
            )
            label = category.label.replace(" ", "\n")
            if "\n" not in label:
                label += "\n"
            ttk.Label(
                entry, text=label, width=1,
                anchor="n", justify="center", font=self.appearance.font,
                foreground=palette.foreground,
            ).grid(row=1, column=0, sticky="ew")
            self._entries.append(entry)
        self._signature = signature
