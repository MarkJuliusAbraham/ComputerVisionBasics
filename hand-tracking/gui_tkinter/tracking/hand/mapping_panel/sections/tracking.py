"""Editable per-gesture tracking options, separate from detection criteria."""

import tkinter as tk
from tkinter import ttk

from gestures.hand_landmarks import FINGER_NAMES, finger_label
from gestures.tracking.settings import GestureTrackingSettings
from gui_tkinter.components.theme import ThemeMetrics
from gui_tkinter.core.change_notifications import ChangeNotifications
from gui_tkinter.core.scaled_layout import ScaledLayout


class GestureTrackingSection(ttk.LabelFrame):
    def __init__(self, master, on_change=None, *, appearance=None):
        super().__init__(master, text="Tracking")
        self.appearance = appearance if appearance is not None else ThemeMetrics(self)
        self.changes = ChangeNotifications(self, on_change)
        self.layout = ScaledLayout(self, self.appearance)
        self.layout.configure(self, padding=16)
        ttk.Label(self, text="Tracked fingertips").pack(anchor="w")
        self.choices = self.layout.pack(ttk.Frame(self), fill="x", pady=12)
        self.variables = {}
        defaults = GestureTrackingSettings()
        for column, name in enumerate(FINGER_NAMES):
            self.choices.columnconfigure(column, weight=1, uniform="tracked_finger")
            variable = tk.BooleanVar(self, value=name in defaults.fingers)
            ttk.Checkbutton(self.choices, text=finger_label(name), variable=variable).grid(
                row=0, column=column, sticky="w",
            )
            self.changes.watch(variable)
            self.variables[name] = variable
        ttk.Label(
            self, text="Each selected fingertip draws its own path.",
            width=1, anchor="w",
        ).pack(fill="x")
        self.optimistic_enabled = tk.BooleanVar(self, value=True)
        self.optimistic_choice = self.layout.pack(ttk.Checkbutton(
            self, text="Use optimistic tracking", variable=self.optimistic_enabled,
        ), anchor="w", pady=(12, 0))
        self.changes.watch(self.optimistic_enabled)

    def load(self, settings, *, use_optimistic_tracking=True):
        with self.changes.suspended():
            self.optimistic_enabled.set(use_optimistic_tracking)
            for name, variable in self.variables.items():
                variable.set(name in settings.fingers)

    def values(self):
        return GestureTrackingSettings(tuple(
            name for name, variable in self.variables.items() if variable.get()
        ))
