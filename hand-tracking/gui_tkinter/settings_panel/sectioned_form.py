"""Shared assembly and draft loading for independently scoped settings forms."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.scrollable_frame import ScrollableFrame


class SectionedSettingsForm(ttk.Frame):
    def __init__(self, master, on_change=None):
        super().__init__(master)
        self._loading = False
        self._on_change = on_change
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        self.sections = {}
        self.variables = {}
        self.status_var = tk.StringVar(self)
        self.validation_error = tk.StringVar(self)

    def add_section(self, name, section):
        self.sections[name] = section
        section.pack(fill="x", pady=(0, 16))
        self.variables.update(getattr(section, "variables", {}))

    def notify_change(self):
        if not self._loading and self._on_change:
            self._on_change()

    def values(self):
        values = {}
        for section in self.sections.values():
            if hasattr(section, "values"):
                values.update(section.values())
        return values

    def load_data(self, data):
        self._loading = True
        try:
            for section in self.sections.values():
                if hasattr(section, "load"):
                    section.load(data)
            self.validation_error.set("")
            self.set_theme(data.theme)
        finally:
            self._loading = False

    def load(self, settings):
        self.load_data(settings.data)

    def set_theme(self, theme_name):
        self.scroll.set_surface()
        for section in self.sections.values():
            if hasattr(section, "set_theme"):
                section.set_theme(theme_name)

    def show_section(self, name):
        section = self.sections.get(name)
        if section is not None:
            self.scroll.scroll_to(section)
