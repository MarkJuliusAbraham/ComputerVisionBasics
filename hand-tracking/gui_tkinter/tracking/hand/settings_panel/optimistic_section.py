"""Wrist activation threshold and timing shared by opted-in gestures."""

import tkinter as tk
from tkinter import ttk

from gestures.optimistic.settings import OptimisticTrackingSettings
from gestures.repeating.settings import AxisWeights, MovementBufferSettings
from gui_tkinter.components.movement_controls import AxisWeightsControl, NumericSettingRow
from gui_tkinter.components.theme import ThemeMetrics


class OptimisticTrackingSection(ttk.LabelFrame):
    def __init__(self, master, on_change=None, *, appearance=None):
        super().__init__(master, text="Optimistic Tracking")
        self.appearance = appearance if appearance is not None else ThemeMetrics(self)
        self._on_change = on_change
        self._loading = False
        self.enabled = tk.BooleanVar(self, value=OptimisticTrackingSettings().enabled)
        self.variables = {
            name: tk.StringVar(self)
            for name in ("lookback", "threshold", "buffer", "credit", "delay", "variance", "x", "y")
        }
        ttk.Checkbutton(self, text="Enable optimistic tracking", variable=self.enabled).pack(anchor="w")
        self.summary = ttk.Label(
            self, text=(
                "Passing the wrist activation distance grants two repeats to the next opted-in gesture, "
                "within its repeat limit."
            ), width=1, wraplength=self.appearance.pixels(420), justify="left",
        )
        self.summary.pack(fill="x")
        self.rows = []
        for name, label, maximum, increment, unit in (
            ("lookback", "Lookback duration", 10, 0.1, "sec"),
            ("threshold", "Activation distance", 100, 0.5, "%"),
            ("buffer", "Starting buffer", 100, 0.5, "%"),
            ("credit", "Buffer credit", 100, 5, "%"),
            ("delay", "Delay between repeats", 10000, 10, "ms"),
            ("variance", "Delay variance", 10000, 5, "ms"),
        ):
            row = NumericSettingRow(
                self, label, self.variables[name], maximum=maximum, increment=increment,
                unit=unit, appearance=self.appearance,
            )
            row.pack(fill="x")
            self.rows.append(row)
        self.axes = AxisWeightsControl(
            self, {name: self.variables[name] for name in ("x", "y")}, self.appearance,
        )
        self.axes.pack(fill="x")
        self.hint = ttk.Label(
            self, text=(
                "Distances: % of image width. Buffer credit counts that share once the buffer is crossed.\n"
                "Axis weights: 0 ignores; 1 counts normally; higher values favor it.\n"
                "Each repeat uses delay ± variance, bounded at zero, after the preceding sequence finishes."
            ), width=1, wraplength=self.appearance.pixels(420), justify="left",
        )
        self.hint.pack(fill="x")
        for variable in (*self.variables.values(), self.enabled):
            variable.trace_add("write", self._changed)
        self.bind("<Configure>", self._wrap_text)
        self.bind("<<ThemeChanged>>", lambda _event: self.after_idle(self._refresh_layout))
        self._refresh_layout()

    def _refresh_layout(self):
        self.appearance.refresh()
        pixels = self.appearance.pixels
        self.configure(padding=pixels(16))
        self.summary.pack_configure(pady=(pixels(10), pixels(8)))
        for row in self.rows:
            row.pack_configure(pady=pixels(6))
            row.refresh_layout()
        self.axes.pack_configure(pady=(pixels(12), 0))
        self.hint.pack_configure(pady=(pixels(6), 0))
        self._wrap_text()

    def _wrap_text(self, _event=None):
        if self.winfo_width() > 1:
            width = max(1, self.winfo_width() - self.appearance.pixels(36))
            for label in (self.summary, self.hint):
                if int(label.cget("wraplength")) != width:
                    label.configure(wraplength=width)

    def draft_values(self):
        return {"optimistic_tracking": {
            "enabled": self.enabled.get(),
            **{name: variable.get() for name, variable in self.variables.items()},
        }}

    def values(self):
        try:
            numbers = {name: float(variable.get()) for name, variable in self.variables.items()}
        except ValueError as error:
            raise ValueError("Optimistic Tracking inputs must be numbers") from error
        return {"optimistic_tracking": OptimisticTrackingSettings(
            enabled=self.enabled.get(), lookback_seconds=numbers["lookback"],
            activation_distance=numbers["threshold"] / 100,
            repeat_delay_ms=numbers["delay"], delay_variance_ms=numbers["variance"],
            movement=MovementBufferSettings(
                initial_displacement=numbers["buffer"] / 100, buffer_credit=numbers["credit"] / 100,
                axis_weights=AxisWeights(x=numbers["x"], y=numbers["y"]),
            ),
        )}

    def load(self, data):
        self._loading = True
        try:
            settings = data.optimistic_tracking
            values = {
                "lookback": settings.lookback_seconds,
                "threshold": settings.activation_distance * 100,
                "buffer": settings.movement.initial_displacement * 100,
                "credit": settings.movement.buffer_credit * 100,
                "delay": settings.repeat_delay_ms,
                "variance": settings.delay_variance_ms,
                "x": settings.movement.axis_weights.x,
                "y": settings.movement.axis_weights.y,
            }
            self.enabled.set(settings.enabled)
            for name, variable in self.variables.items():
                variable.set(format(values[name], ".12g"))
        finally:
            self._loading = False

    def _changed(self, *_args):
        if not self._loading and self._on_change:
            self._on_change()
