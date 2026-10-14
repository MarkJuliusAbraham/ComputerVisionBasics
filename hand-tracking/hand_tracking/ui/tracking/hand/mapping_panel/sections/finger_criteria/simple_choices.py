"""The dropdown view of common finger criteria combinations."""

import tkinter as tk
from tkinter import ttk
from hand_tracking.ui.core.change_notifications import ChangeNotifications

from ..criteria_options import CUSTOM_CLASSIFICATIONS, FINGER_NAMES
from .table import FingerCriteriaTable


class SimpleChoicesTable(FingerCriteriaTable):
    """Translate dropdown interaction into selection-model operations."""

    def __init__(self, master, appearance, on_select):
        super().__init__(master, appearance)
        self._on_select = on_select
        self.changes = ChangeNotifications(self)
        self.variables = {}
        self.selectors = {}
        self.heading("Allowed position", 1)
        self.columnconfigure(1, weight=1, minsize=0)
        self.set_column_count(2)
        for index, name in enumerate(FINGER_NAMES):
            variable = tk.StringVar(self, value="Any position")
            selector = ttk.Combobox(
                self, textvariable=variable, state="readonly", width=1,
            )
            selector.grid(row=self.finger_row(index), column=1, sticky="ew")
            self.variables[name] = variable
            self.selectors[name] = selector
            self.changes.watch(variable, callback=lambda finger=name: self._changed(finger))

    @property
    def controls(self):
        return tuple(self.selectors.values())

    def load(self, model):
        with self.changes.suspended():
            for name, variable in self.variables.items():
                label = model.label_for(name)
                choices = tuple(model.options.simple_choices)
                if label == CUSTOM_CLASSIFICATIONS:
                    choices += (CUSTOM_CLASSIFICATIONS,)
                self.selectors[name].configure(values=choices)
                if variable.get() != label:
                    variable.set(label)

    def _changed(self, name):
        self._on_select(name, self.variables[name].get())
