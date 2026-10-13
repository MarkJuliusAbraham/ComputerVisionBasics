"""Reusable declarative, aligned settings fields independent of a panel."""

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk

from gui_tkinter.core.change_notifications import ChangeNotifications
from gui_tkinter.core.idle_refresh import IdleRefresh

from .theme import ThemeMetrics


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    kind: str
    options: tuple[str, ...] = ()
    minimum: float = 0.0
    maximum: float = 0.0
    increment: float = 1.0


class FieldSection(ttk.LabelFrame):
    def __init__(self, master, title, fields, on_change=None):
        super().__init__(master, text=title)
        self.appearance = ThemeMetrics(self)
        self.changes = ChangeNotifications(self, on_change)
        self.fields = tuple(fields)
        self.variables = {}
        self.rows = []
        for field in self.fields:
            self._add_field(field)
        self.theme_refresh = IdleRefresh(self, self._refresh_layout, event="<<ThemeChanged>>")
        self._refresh_layout()

    def _add_field(self, field):
        row = ttk.Frame(self)
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)
        self.rows.append(row)
        if field.kind == "check":
            variable = tk.BooleanVar(self)
            ttk.Checkbutton(row, text=field.label, variable=variable).grid(row=0, column=0, sticky="w")
        else:
            # Preserve incomplete numeric input until Apply validates it.
            variable = tk.StringVar(self)
            ttk.Label(row, text=field.label).grid(row=0, column=0, sticky="w")
            if field.kind == "number":
                control = ttk.Spinbox(
                    row, textvariable=variable, from_=field.minimum, to=field.maximum,
                    increment=field.increment, width=9,
                )
            elif field.kind == "choice":
                control = ttk.Combobox(
                    row, textvariable=variable, values=field.options, state="readonly", width=14,
                )
            else:
                raise ValueError(f"Unknown field kind: {field.kind}")
            control.grid(row=0, column=1, sticky="e")
        self.variables[field.key] = variable
        # One trace covers typing, arrow clicks, and dropdown selection.
        self.changes.watch(variable)

    def _refresh_layout(self):
        self.appearance.refresh()
        pixels = self.appearance.pixels
        self.configure(padding=(pixels(12), pixels(8), pixels(12), pixels(10)))
        for row in self.rows:
            row.pack_configure(pady=pixels(4))
            for child in row.winfo_children():
                if isinstance(child, ttk.Label):
                    child.grid_configure(padx=(0, pixels(12)))

    def draft_values(self):
        return {key: variable.get() for key, variable in self.variables.items()}

    def values(self):
        values = self.draft_values()
        for field in self.fields:
            if field.kind == "number":
                try:
                    values[field.key] = float(values[field.key])
                except ValueError as error:
                    raise ValueError(f"{field.label} must be a number") from error
        return values

    def load_values(self, values):
        with self.changes.suspended():
            for key, variable in self.variables.items():
                if key in values and values[key] is not None:
                    variable.set(values[key])
