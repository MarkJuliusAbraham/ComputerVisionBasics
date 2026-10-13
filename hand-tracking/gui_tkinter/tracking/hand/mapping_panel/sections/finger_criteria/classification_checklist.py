"""The classification checkbox view of finger criteria."""

import tkinter as tk
from tkinter import ttk
from gui_tkinter.core.change_notifications import ChangeNotifications

from ..criteria_options import FINGER_NAMES, FINGER_OPTIONS
from .table import FingerCriteriaTable


class ClassificationChecklist(FingerCriteriaTable):
    """Show active classifications and retain selected inactive classifications."""

    def __init__(self, master, appearance, on_toggle):
        super().__init__(master, appearance)
        self._on_toggle = on_toggle
        self.changes = ChangeNotifications(self)
        self._columns_key = None
        self.variables = {name: {} for name in FINGER_NAMES}
        self.checkboxes = {name: {} for name in FINGER_NAMES}
        self.headings = {
            position: self.heading(position.replace("_", "\n").title(), column, center=True)
            for column, position in enumerate(FINGER_OPTIONS, start=1)
        }
        for index, name in enumerate(FINGER_NAMES):
            for column, position in enumerate(FINGER_OPTIONS, start=1):
                variable = tk.BooleanVar(self)
                checkbox = ttk.Checkbutton(self, variable=variable)
                checkbox.grid(row=self.finger_row(index), column=column)
                self.variables[name][position] = variable
                self.checkboxes[name][position] = checkbox
                self.changes.watch(
                    variable, callback=lambda finger=name, classification=position:
                    self._changed(finger, classification),
                )

    @property
    def controls(self):
        return tuple(checkbox for row in self.checkboxes.values() for checkbox in row.values())

    def load(self, model):
        with self.changes.suspended():
            selections = model.values()
            for name, variables in self.variables.items():
                for position, variable in variables.items():
                    selected = position in selections[name]
                    if variable.get() != selected:
                        variable.set(selected)
                    self.checkboxes[name][position].state(
                        ["!disabled"] if selected or position in model.options.positions
                        else ["disabled"]
                    )
            self._show_columns(model)

    def _show_columns(self, model):
        visible = model.visible_positions
        key = (model.options.positions, visible)
        if key == self._columns_key:
            return
        for column in range(1, len(FINGER_OPTIONS) + 1):
            self.columnconfigure(column, minsize=0, weight=0, uniform="")
        for position, heading in self.headings.items():
            heading.grid_remove()
            for row in self.checkboxes.values():
                row[position].grid_remove()
        for column, position in enumerate(visible, start=1):
            active = position in model.options.positions
            heading = self.headings[position]
            heading.configure(
                text=position.replace("_", "\n").title() + ("" if active else "\n(inactive)"),
            )
            heading.state(["!disabled"] if active else ["disabled"])
            heading.grid(row=0, column=column, sticky="ew")
            # Data columns share available space; layout refreshes never add
            # rigid minimum widths that can push them outside this frame.
            self.columnconfigure(column, minsize=0, weight=1, uniform="position")
            for row in self.checkboxes.values():
                row[position].grid(column=column)
        self.set_column_count(len(visible) + 1)
        self._columns_key = key

    def _changed(self, name, position):
        self._on_toggle(name, position, self.variables[name][position].get())
