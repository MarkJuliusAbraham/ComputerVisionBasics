"""Coordinate the selection model and its two interchangeable table views."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.theme import ThemeMetrics

from .classification_checklist import ClassificationChecklist
from .layout import FingerCriteriaLayout
from .selection_model import FingerSelectionModel
from .simple_choices import SimpleChoicesTable


class FingerCriteriaEditor(ttk.Frame):
    """Expose finger criteria while delegating state, rendering, and geometry."""

    def __init__(self, master, on_change=None, appearance=None, segment_count=4):
        super().__init__(master)
        self.appearance = appearance or ThemeMetrics(self)
        self._on_change = on_change
        self._mode = "straightness"
        self.model = FingerSelectionModel(segment_count)
        self.availability_message = tk.StringVar(self)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.grid_propagate(False)
        self.simple_choices = SimpleChoicesTable(self, self.appearance, self._choice_changed)
        self.checklist = ClassificationChecklist(self, self.appearance, self._check_changed)
        for table in (self.simple_choices, self.checklist):
            table.grid(row=0, column=0, sticky="nsew")
        self.layout = FingerCriteriaLayout(
            self, self.appearance, (self.simple_choices, self.checklist),
        )
        self._render()
        self._show_mode()
        self.layout.refresh()
        self.layout.schedule_refresh()
        self.bind("<<ThemeChanged>>", self.layout.schedule_refresh)
        self.bind("<Destroy>", self.layout.widget_destroyed)

    @property
    def mode(self):
        return self._mode

    @property
    def segment_count(self):
        return self.model.options.segment_count

    @property
    def label_width(self):
        return self.layout.label_width

    def values(self):
        return self.model.values()

    def load(self, fingers):
        self.model.load(fingers)
        self._render()

    def set_segment_count(self, segment_count):
        self.model.set_segment_count(segment_count)
        self._render()

    def toggle_mode(self):
        self._mode = "classifications" if self._mode == "straightness" else "straightness"
        self._show_mode()

    def _show_mode(self):
        selected, hidden = (
            (self.simple_choices, self.checklist) if self._mode == "straightness"
            else (self.checklist, self.simple_choices)
        )
        hidden.grid_remove()
        selected.grid()

    def _render(self):
        self.simple_choices.load(self.model)
        self.checklist.load(self.model)
        message = self.model.availability_message
        if self.availability_message.get() != message:
            self.availability_message.set(message)

    def _choice_changed(self, name, label):
        if self.model.choose(name, label):
            self._notify_change()

    def _check_changed(self, name, position, checked):
        if self.model.set_checked(name, position, checked):
            self._notify_change()

    def _notify_change(self):
        self._render()
        if self._on_change:
            self._on_change()
