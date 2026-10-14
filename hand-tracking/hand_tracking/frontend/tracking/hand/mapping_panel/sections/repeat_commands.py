"""Movement repeat controls and the scope of their pending mapping edits."""

import tkinter as tk
from tkinter import ttk

from hand_tracking.frontend.components.movement_controls import MovementSettingsControls
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
                "While this gesture is detected, average movement across its tracked fingertips repeats its commands.\n"
                "All tracked fingers share the repeat limit until reset."
            ), width=1, anchor="w", justify="left", wraplength=appearance.pixels(500),
        ), fill="x", pady=(10, 12))
        self.movement = MovementSettingsControls(self, appearance, on_change=self._changed)
        self.movement.pack(fill="x")
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

    def values(self):
        return self.movement.values()

    def _scope_changed(self):
        if self.apply_to_all.get():
            self._changed()

    def _changed(self):
        if self._on_change:
            self._on_change()
