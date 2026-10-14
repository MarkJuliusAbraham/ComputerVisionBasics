"""Wrist activation threshold and timing shared by opted-in gestures."""

import tkinter as tk
from tkinter import ttk

from hand_tracking.gestures.optimistic.settings import OptimisticTrackingSettings
from hand_tracking.ui.components.movement_controls import (
    BUFFER_CREDIT,
    STARTING_BUFFER,
    NumericField,
    NumericFieldGroup,
)
from hand_tracking.ui.components.movement_draft import (
    buffer_from_numbers,
    buffer_texts,
    number_text,
    parse_numbers,
    percent_text,
)
from hand_tracking.ui.components.text_wrap import WrapToWidth
from hand_tracking.ui.components.theme import ThemeMetrics
from hand_tracking.ui.core.change_notifications import ChangeNotifications
from hand_tracking.ui.core.scaled_layout import ScaledLayout

WRIST_AXES = ("x", "y")
FIELDS = (
    NumericField("lookback", "Lookback duration", 10, 0.1, "sec"),
    NumericField("threshold", "Activation distance", 100, 0.5, "%"),
    STARTING_BUFFER,
    BUFFER_CREDIT,
    NumericField("delay", "Delay between repeats", 10000, 10, "ms"),
    NumericField("variance", "Delay variance", 10000, 5, "ms"),
)


class OptimisticTrackingSection(ttk.LabelFrame):
    def __init__(self, master, on_change=None, *, appearance=None):
        super().__init__(master, text="Optimistic Tracking")
        self.appearance = appearance if appearance is not None else ThemeMetrics(self)
        self.changes = ChangeNotifications(self, on_change)
        self.enabled = tk.BooleanVar(self, value=OptimisticTrackingSettings().enabled)
        ttk.Checkbutton(self, text="Enable optimistic tracking", variable=self.enabled).pack(anchor="w")
        self.layout = ScaledLayout(self, self.appearance, on_refresh=lambda: self.wrap.refresh())
        self.layout.configure(self, padding=16)
        self.summary = self.layout.pack(ttk.Label(
            self, text=(
                "Passing the wrist activation distance grants two repeats to the next opted-in gesture, "
                "within its repeat limit."
            ), width=1, wraplength=self.appearance.pixels(420), justify="left",
        ), fill="x", pady=(10, 8))
        self.fields = NumericFieldGroup(self, self.appearance, FIELDS, WRIST_AXES, on_change=self.changes.emit)
        self.fields.pack(fill="x")
        self.variables = self.fields.variables
        self.hint = self.layout.pack(ttk.Label(
            self, text=(
                "Distances: % of image width. Buffer credit counts that share once the buffer is crossed.\n"
                "Axis weights: 0 ignores; 1 counts normally; higher values favor it.\n"
                "Each repeat uses delay ± variance, bounded at zero, after the preceding sequence finishes."
            ), width=1, wraplength=self.appearance.pixels(420), justify="left",
        ), fill="x", pady=(6, 0))
        self.wrap = WrapToWidth(self, (self.summary, self.hint), self.appearance)
        self.changes.watch(self.enabled)

    def draft_values(self):
        return {"optimistic_tracking": {"enabled": self.enabled.get(), **self.fields.draft_values()}}

    def values(self):
        numbers = parse_numbers(self.fields.draft_values(), "Optimistic Tracking inputs must be numbers")
        return {"optimistic_tracking": OptimisticTrackingSettings(
            enabled=self.enabled.get(), lookback_seconds=numbers["lookback"],
            activation_distance=numbers["threshold"] / 100,
            repeat_delay_ms=numbers["delay"], delay_variance_ms=numbers["variance"],
            movement=buffer_from_numbers(numbers, WRIST_AXES),
        )}

    def load(self, data):
        settings = data.optimistic_tracking
        with self.changes.suspended():
            self.enabled.set(settings.enabled)
            self.fields.load_texts({
                "lookback": number_text(settings.lookback_seconds),
                "threshold": percent_text(settings.activation_distance),
                "delay": number_text(settings.repeat_delay_ms),
                "variance": number_text(settings.delay_variance_ms),
                **buffer_texts(settings.movement, WRIST_AXES),
            })
