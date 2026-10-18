"""Movement repeat controls and the scope of their pending mapping edits."""

import tkinter as tk
from dataclasses import replace
from tkinter import ttk

from hand_tracking.frontend.components.movement_controls import (
    MovementSettingsControls, NumericField, NumericFieldGroup,
)
from hand_tracking.frontend.components.text_wrap import WrapToWidth
from hand_tracking.frontend.core.scaled_layout import ScaledLayout


class RepeatCommandsSection(ttk.LabelFrame):
    def __init__(self, master, appearance, on_change=None):
        super().__init__(master, text="Repeat Commands")
        self.appearance = appearance
        self._on_change = on_change
        self.apply_to_all = tk.BooleanVar(self, value=True)
        self.scope = ttk.Checkbutton(
            self, text="Apply to all gestures", variable=self.apply_to_all,
            command=self._scope_changed,
        )
        self.scope.pack(anchor="e")
        self.layout = ScaledLayout(self, appearance, on_refresh=lambda: self.wrap.refresh())
        self.layout.configure(self, padding=16)
        self.summary = self.layout.pack(ttk.Label(
            self, text=(
                "Tracking repeats the held gesture; Distance and Shake remember the triggered gesture.\n"
                "Both modes share the repeat limit until reset."
            ), width=1, anchor="w", justify="left", wraplength=appearance.pixels(500),
        ), fill="x", pady=(10, 12))
        self.trigger = tk.StringVar(self, value="Tracking")
        selector = self.layout.pack(ttk.Frame(self), fill="x", pady=(0, 8))
        ttk.Label(selector, text="Repeat trigger").pack(side="left")
        self.trigger_choice = ttk.Combobox(
            selector, textvariable=self.trigger, values=("Tracking", "Distance", "Shake"),
            state="readonly", width=12,
        )
        self.trigger_choice.pack(side="right")
        self.trigger_choice.bind("<<ComboboxSelected>>", self._trigger_changed)
        self.movement = MovementSettingsControls(
            self, appearance, on_change=self._changed, include_interval=True,
        )
        self.movement.pack(fill="x")
        self.distance = NumericFieldGroup(self, appearance, (
            NumericField("distance", "Distance per repeat", 100, 0.5, "%"),
            NumericField("limit", "Repeat limit", 1000, 1, "times"),
            NumericField("interval", "Delay between repeats", 10000, 10, "ms"),
        ), ("x", "y", "z"), on_change=self._changed)
        self._shown_trigger = "Tracking"
        self.shake = NumericFieldGroup(self, appearance, (
            NumericField("amplitude", "Travel per shake (% palm width)", 300, 5, "%"),
            NumericField("window", "Shake time window", 3000, 50, "ms"),
            NumericField("limit", "Repeat limit", 1000, 1, "times"),
            NumericField("interval", "Delay between repeats", 10000, 10, "ms"),
        ), (), on_change=self._changed)
        self.hint = self.layout.pack(ttk.Label(
            self, text=(
                "Distances are % of image width. A limit of 0 disables repeats.\n"
                "Buffer credit counts that % of the buffer after it is crossed.\n"
                "0 ignores an axis; 1 counts normally; higher values favor it. Z uses relative depth."
            ), width=1, anchor="w", justify="left", wraplength=appearance.pixels(500),
        ), fill="x", pady=(8, 0))
        self.wrap = WrapToWidth(self, (self.summary, self.hint), appearance)

    def load(self, draft):
        self.movement.load(draft)
        self.shake.load_texts({
            "amplitude": draft.shake_amplitude, "window": draft.shake_window_ms,
            "limit": draft.limit, "interval": str(draft.min_interval_seconds * 1000),
        })
        self.distance.load_texts({
            "distance": draft.distance, "limit": draft.limit,
            "interval": str(draft.min_interval_seconds * 1000),
            **{axis: getattr(draft, axis) for axis in ("x", "y", "z")},
        })
        self.trigger.set(draft.trigger.title())
        self._show_trigger()

    def values(self):
        values = self.shake.draft_values()
        draft = replace(
            self.movement.values(), trigger=self.trigger.get().lower(),
            shake_amplitude=values["amplitude"], shake_window_ms=values["window"],
        )
        if draft.trigger == "shake":
            try:
                interval = float(values["interval"]) / 1000
            except ValueError as error:
                raise ValueError("Repeat delay must be a number of milliseconds") from error
            draft = replace(draft, limit=values["limit"], min_interval_seconds=interval)
        elif draft.trigger == "distance":
            values = self.distance.draft_values()
            try:
                interval = float(values.pop("interval")) / 1000
            except ValueError as error:
                raise ValueError("Repeat delay must be a number of milliseconds") from error
            draft = replace(draft, **values, min_interval_seconds=interval)
        return draft

    def _trigger_changed(self, _event=None):
        # Limit and delay mean the same thing in either mode.
        groups = {"Shake": self.shake, "Distance": self.distance, "Tracking": self.movement}
        source = groups[self._shown_trigger]
        target = groups[self.trigger.get()]
        with target.changes.suspended():
            for name in source.variables.keys() & target.variables.keys():
                target.variables[name].set(source.variables[name].get())
        self._show_trigger()
        self._changed()

    def _show_trigger(self):
        shaking = self.trigger.get() == "Shake"
        self.movement.pack_forget()
        self.shake.pack_forget()
        self.distance.pack_forget()
        self._shown_trigger = self.trigger.get()
        groups = {"Shake": self.shake, "Distance": self.distance, "Tracking": self.movement}
        groups[self._shown_trigger].pack(fill="x", before=self.hint)
        self.hint.configure(text=(
            "Trigger a gesture, then shake to repeat it even if your finger pose changes.\n"
            "Wrist and all fingertips share the travel measurement; return near their starting points.\n"
            "The gesture stays remembered until reset, including across pauses or hand loss."
            if shaking else
            "Every X distance traveled by the selected fingertips earns one repeat.\n"
            "Their distances are averaged. Leftover distance carries forward; no starting buffer.\n"
            "The triggered gesture is remembered until reset. Distances are % of image width."
            if self._shown_trigger == "Distance" else
            "Distances are % of image width. A limit of 0 disables repeats.\n"
            "Buffer credit counts that % of the buffer after it is crossed.\n"
            "0 ignores an axis; 1 counts normally; higher values favor it. Z uses relative depth."
        ))
        self.wrap.refresh()

    def _scope_changed(self):
        if self.apply_to_all.get():
            self._changed()

    def _changed(self):
        if self._on_change:
            self._on_change()
