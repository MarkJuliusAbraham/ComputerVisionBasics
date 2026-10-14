"""Shared assembly and draft loading for independently scoped settings forms."""

import tkinter as tk
from tkinter import ttk
from hand_tracking.ui.core.change_notifications import ChangeNotifications


class SectionedSettingsForm(ttk.Frame):
    def __init__(self, master, on_change=None):
        super().__init__(master)
        self.changes = ChangeNotifications(self, on_change)
        self.content = ttk.Frame(self)
        self.content.pack(fill="both", expand=True)
        self.sections = {}
        self.variables = {}
        self.status_var = tk.StringVar(self)
        self.validation_error = tk.StringVar(self)
        # A ScaledLayout, when set, scales the padding in grid options.
        self.layout = None

    def add_section(self, name, section, **grid_options):
        self.sections[name] = section
        if grid_options:
            place = self.layout.grid if self.layout is not None else type(section).grid
            place(section, sticky="new", **grid_options)
        else:
            section.pack(fill="x", pady=(0, 16))
        self.variables.update(getattr(section, "variables", {}))

    def notify_change(self):
        self.changes.emit()

    def values(self):
        values = {}
        for section in self.sections.values():
            if hasattr(section, "values"):
                values.update(section.values())
        return values

    def draft_values(self):
        values = {}
        for section in self.sections.values():
            getter = getattr(section, "draft_values", None) or getattr(section, "values", None)
            if getter is not None:
                values.update(getter())
        return values

    def load_data(self, data):
        with self.changes.suspended():
            for section in self.sections.values():
                if hasattr(section, "load"):
                    section.load(data)
            self.validation_error.set("")
            self.set_theme(data.theme)

    def load(self, settings):
        self.load_data(settings.data)

    def set_theme(self, theme_name):
        for section in self.sections.values():
            if hasattr(section, "set_theme"):
                section.set_theme(theme_name)
