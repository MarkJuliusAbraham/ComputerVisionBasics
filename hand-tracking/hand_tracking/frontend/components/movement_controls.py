"""Reusable distance, buffer, axis, repeat-count, and timing controls."""

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk

from hand_tracking.frontend.core.change_notifications import ChangeNotifications
from hand_tracking.frontend.core.scaled_layout import ScaledLayout

from .movement_draft import MovementSettingsDraft, number_text


@dataclass(frozen=True)
class NumericField:
    """One labeled numeric input: its form key, label, range, step, and unit."""

    key: str
    label: str
    maximum: float
    increment: float
    unit: str


# Shared by gesture repeats and optimistic tracking.
STARTING_BUFFER = NumericField("buffer", "Starting buffer", 100, 0.5, "%")
BUFFER_CREDIT = NumericField("credit", "Buffer credit", 100, 5, "%")


class NumericSettingRow(ttk.Frame):
    def __init__(self, master, field: NumericField, variable, *, appearance):
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=field.label).grid(row=0, column=0, sticky="w")
        self.layout = ScaledLayout(self, appearance)
        self.input = self.layout.grid(ttk.Spinbox(
            self, textvariable=variable, from_=0, to=field.maximum, increment=field.increment, width=8,
        ), row=0, column=1, padx=(12, 6))
        ttk.Label(self, text=field.unit, width=5, anchor="w").grid(row=0, column=2, sticky="w")


class AxisWeightsControl(ttk.Frame):
    """Render only the axes supplied by the owning settings component."""

    def __init__(self, master, variables, appearance):
        super().__init__(master)
        ttk.Label(self, text="Axis weights", font=appearance.heading_font).pack(anchor="w")
        self.layout = ScaledLayout(self, appearance)
        self.choices = self.layout.pack(ttk.Frame(self), fill="x", pady=(8, 10))
        for column, (name, variable) in enumerate(variables.items()):
            self.choices.columnconfigure(column, weight=1, uniform="movement_axis")
            group = self.layout.grid(ttk.Frame(self.choices), row=0, column=column, sticky="ew", padx=(0, 8))
            ttk.Label(group, text=name.upper()).pack(side="left")
            self.layout.pack(ttk.Spinbox(
                group, textvariable=variable, from_=0, to=10, increment=0.25, width=6,
            ), side="left", padx=8)


class NumericFieldGroup(ttk.Frame):
    """Numeric rows followed by axis weights, reporting edits through one hook.

    Values stay as the text the user typed; owners convert them on Apply/Save.
    """

    def __init__(self, master, appearance, fields, axes, on_change=None):
        super().__init__(master)
        self.changes = ChangeNotifications(self, on_change)
        self.variables = {
            name: tk.StringVar(self) for name in (*(field.key for field in fields), *axes)
        }
        layout = ScaledLayout(self, appearance)
        for field in fields:
            layout.pack(
                NumericSettingRow(self, field, self.variables[field.key], appearance=appearance),
                fill="x", pady=6,
            )
        self.axes = layout.pack(
            AxisWeightsControl(self, {axis: self.variables[axis] for axis in axes}, appearance),
            fill="x", pady=(12, 0),
        ) if axes else None
        self.changes.watch(*self.variables.values())

    def draft_values(self):
        return {name: variable.get() for name, variable in self.variables.items()}

    def load_texts(self, texts):
        with self.changes.suspended():
            for name, variable in self.variables.items():
                variable.set(texts[name])


class MovementSettingsControls(NumericFieldGroup):
    def __init__(
        self, master, appearance, on_change=None, *, include_interval=False,
        limit_label="Repeat limit",
    ):
        fields = [
            NumericField("distance", "Distance per repeat", 100, 0.5, "%"),
            STARTING_BUFFER,
            BUFFER_CREDIT,
            NumericField("limit", limit_label, 1000, 1, "times"),
        ]
        if include_interval:
            fields.append(NumericField("interval", "Delay between repeats", 10000, 10, "ms"))
        super().__init__(master, appearance, fields, ("x", "y", "z"), on_change)
        self.include_interval = include_interval
        self.load(MovementSettingsDraft.defaults())

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
        self._interval = draft.min_interval_seconds
        texts = {name: getattr(draft, name) for name in self.variables if name != "interval"}
        if self.include_interval:
            texts["interval"] = number_text(self._interval * 1000)
        self.load_texts(texts)
