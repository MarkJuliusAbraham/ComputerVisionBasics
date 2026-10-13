"""Reusable distance, buffer, axis, repeat-count, and timing controls."""

import tkinter as tk
from tkinter import ttk
from gui_tkinter.core.idle_refresh import IdleRefresh
from gui_tkinter.core.change_notifications import ChangeNotifications

from .movement_draft import MovementSettingsDraft


class NumericSettingRow(ttk.Frame):
    def __init__(self, master, label, variable, *, maximum, increment, unit, appearance):
        super().__init__(master)
        self.appearance = appearance
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=label).grid(row=0, column=0, sticky="w")
        self.input = ttk.Spinbox(
            self, textvariable=variable, from_=0, to=maximum, increment=increment, width=8,
        )
        self.input.grid(row=0, column=1)
        ttk.Label(self, text=unit, width=5, anchor="w").grid(row=0, column=2, sticky="w")
        self.refresh_layout()

    def refresh_layout(self):
        self.input.grid_configure(padx=(self.appearance.pixels(12), self.appearance.pixels(6)))


class AxisWeightsControl(ttk.Frame):
    """Render only the axes supplied by the owning settings component."""

    def __init__(self, master, variables, appearance):
        super().__init__(master)
        self.appearance = appearance
        ttk.Label(self, text="Axis weights", font=appearance.heading_font).pack(anchor="w")
        self.choices = ttk.Frame(self)
        self.choices.pack(fill="x")
        self.inputs = []
        for column, (name, variable) in enumerate(variables.items()):
            self.choices.columnconfigure(column, weight=1, uniform="movement_axis")
            group = ttk.Frame(self.choices)
            group.grid(row=0, column=column, sticky="ew")
            ttk.Label(group, text=name.upper()).pack(side="left")
            spin = ttk.Spinbox(group, textvariable=variable, from_=0, to=10, increment=0.25, width=6)
            spin.pack(side="left")
            self.inputs.append((group, spin))
        self.theme_refresh = IdleRefresh(self, self.refresh_layout, event="<<ThemeChanged>>")
        self.refresh_layout()

    def refresh_layout(self):
        self.appearance.refresh()
        pixels = self.appearance.pixels
        self.choices.pack_configure(pady=(pixels(8), pixels(10)))
        for group, spin in self.inputs:
            group.grid_configure(padx=(0, pixels(8)))
            spin.pack_configure(padx=pixels(8))


class MovementSettingsControls(ttk.Frame):
    def __init__(
        self, master, appearance, on_change=None, *, include_interval=False,
        limit_label="Repeat limit",
    ):
        super().__init__(master)
        self.appearance = appearance
        self.changes = ChangeNotifications(self, on_change)
        self.include_interval = include_interval
        defaults = MovementSettingsDraft.defaults()
        self._interval = defaults.min_interval_seconds
        self.variables = {
            name: tk.StringVar(self, value=getattr(defaults, name))
            for name in ("distance", "buffer", "credit", "limit", "x", "y", "z")
        }
        fields = [
            ("distance", "Distance per repeat", 100, 0.5, "%"),
            ("buffer", "Starting buffer", 100, 0.5, "%"),
            ("credit", "Buffer credit", 100, 5, "%"),
            ("limit", limit_label, 1000, 1, "times"),
        ]
        if include_interval:
            self.variables["interval"] = tk.StringVar(self, value=str(self._interval * 1000))
            fields.append(("interval", "Delay between repeats", 10000, 10, "ms"))
        self.rows = []
        for name, label, maximum, increment, unit in fields:
            row = NumericSettingRow(
                self, label, self.variables[name], maximum=maximum, increment=increment,
                unit=unit, appearance=appearance,
            )
            row.pack(fill="x")
            self.rows.append(row)
        self.axes = AxisWeightsControl(
            self, {name: self.variables[name] for name in ("x", "y", "z")}, appearance,
        )
        self.axes.pack(fill="x")
        self.changes.watch(*self.variables.values())
        self.theme_refresh = IdleRefresh(self, self._refresh_layout, event="<<ThemeChanged>>")
        self._refresh_layout()

    def _refresh_layout(self):
        self.appearance.refresh()
        pixels = self.appearance.pixels
        for row in self.rows:
            row.pack_configure(pady=pixels(6))
            row.refresh_layout()
        self.axes.pack_configure(pady=(pixels(12), 0))
        self.axes.refresh_layout()

    def draft_values(self):
        return {name: variable.get() for name, variable in self.variables.items()}

    def values(self):
        values = self.draft_values()
        interval = self._interval
        if self.include_interval:
            try:
                interval = float(values.pop("interval")) / 1000
            except ValueError as error:
                raise ValueError("Repeat delay must be a number of milliseconds") from error
        return MovementSettingsDraft(**values, min_interval_seconds=interval)

    def load(self, draft):
        with self.changes.suspended():
            self._interval = draft.min_interval_seconds
            for name, variable in self.variables.items():
                value = format(self._interval * 1000, ".12g") if name == "interval" else getattr(draft, name)
                variable.set(value)
