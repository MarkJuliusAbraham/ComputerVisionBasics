"""Movement repeat controls and the scope of their pending mapping edits."""

from gui_tkinter.core.idle_refresh import IdleRefresh
import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.movement_controls import MovementSettingsControls


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
        self.summary = ttk.Label(
            self, text=(
                "While this gesture is detected, average movement across its tracked fingertips repeats its commands.\n"
                "All tracked fingers share the repeat limit until reset."
            ), width=1, anchor="w", justify="left", wraplength=appearance.pixels(500),
        )
        self.summary.pack(fill="x")
        self.movement = MovementSettingsControls(self, appearance, on_change=self._changed)
        self.movement.pack(fill="x")
        self.hint = ttk.Label(
            self, text=(
                "Distances are % of image width. A limit of 0 disables repeats.\n"
                "Buffer credit counts that % of the buffer after it is crossed.\n"
                "0 ignores an axis; 1 counts normally; higher values favor it. Z uses relative depth."
            ), width=1, anchor="w", justify="left", wraplength=appearance.pixels(500),
        )
        self.hint.pack(fill="x")
        self.bind("<Configure>", self._wrap_text)
        self.theme_refresh = IdleRefresh(self, self._refresh_layout, event="<<ThemeChanged>>")
        self._refresh_layout()

    def _refresh_layout(self):
        self.appearance.refresh()
        pixels = self.appearance.pixels
        self.configure(padding=pixels(16))
        self.summary.pack_configure(pady=(pixels(10), pixels(12)))
        self.hint.pack_configure(pady=(pixels(8), 0))
        self._wrap_text()

    def _wrap_text(self, _event=None):
        if self.winfo_width() <= 1:
            return
        width = max(1, self.winfo_width() - self.appearance.pixels(36))
        for label in (self.summary, self.hint):
            if int(label.cget("wraplength")) != width:
                label.configure(wraplength=width)

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
