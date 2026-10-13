"""Editable per-gesture tracking options, separate from detection criteria."""

from gui_tkinter.core.idle_refresh import IdleRefresh
import tkinter as tk
from tkinter import ttk

from gestures.finger_classifier import FINGERS
from gestures.tracking.settings import GestureTrackingSettings
from gui_tkinter.components.theme import ThemeMetrics
from gui_tkinter.core.change_notifications import ChangeNotifications


class GestureTrackingSection(ttk.LabelFrame):
    def __init__(self, master, on_change=None, *, appearance=None):
        super().__init__(master, text="Tracking")
        self.appearance = appearance if appearance is not None else ThemeMetrics(self)
        self.changes = ChangeNotifications(self, on_change)
        ttk.Label(self, text="Tracked fingertips").pack(anchor="w")
        self.choices = ttk.Frame(self)
        self.choices.pack(fill="x")
        self.variables = {}
        defaults = GestureTrackingSettings()
        for column, name in enumerate(FINGERS):
            self.choices.columnconfigure(column, weight=1, uniform="tracked_finger")
            variable = tk.BooleanVar(self, value=name in defaults.fingers)
            ttk.Checkbutton(self.choices, text=name.title(), variable=variable).grid(
                row=0, column=column, sticky="w",
            )
            self.changes.watch(variable)
            self.variables[name] = variable
        ttk.Label(
            self, text="Each selected fingertip draws its own path.",
            width=1, anchor="w",
        ).pack(fill="x")
        self.optimistic_enabled = tk.BooleanVar(self, value=True)
        self.optimistic_choice = ttk.Checkbutton(
            self, text="Use optimistic tracking", variable=self.optimistic_enabled,
        )
        self.optimistic_choice.pack(anchor="w")
        self.changes.watch(self.optimistic_enabled)
        self._refresh_layout()
        self.theme_refresh = IdleRefresh(self, self._refresh_layout, event="<<ThemeChanged>>")

    def _refresh_layout(self):
        self.appearance.refresh()
        self.configure(padding=self.appearance.pixels(16))
        self.choices.pack_configure(pady=self.appearance.pixels(12))
        self.optimistic_choice.pack_configure(pady=(self.appearance.pixels(12), 0))

    def load(self, settings, *, use_optimistic_tracking=True):
        with self.changes.suspended():
            self.optimistic_enabled.set(use_optimistic_tracking)
            for name, variable in self.variables.items():
                variable.set(name in settings.fingers)

    def values(self):
        return GestureTrackingSettings(tuple(
            name for name, variable in self.variables.items() if variable.get()
        ))
