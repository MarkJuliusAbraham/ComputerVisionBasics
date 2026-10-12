"""Finger criteria controls with interchangeable editing modes."""

import tkinter as tk
from tkinter import ttk

from .criteria_options import (
    CUSTOM_CLASSIFICATIONS,
    FINGER_NAMES,
    FINGER_OPTIONS,
    STRAIGHTNESS_OPTIONS,
)


class FingerCriteriaEditor(ttk.Frame):
    """Own the controls and synchronization for both finger selection modes."""

    def __init__(self, master, on_change=None):
        super().__init__(master)
        self._on_change = on_change
        self._loading = False
        self._mode = "straightness"
        self._selections = {}
        self.columnconfigure(0, weight=1)
        self.straightness = ttk.Frame(self)
        self.classifications = ttk.Frame(self)
        self.straightness_variables = {}
        self.classification_variables = {}
        self._build_straightness()
        self._build_classifications()
        self.straightness.grid(row=0, column=0, sticky="ew")
        self.classifications.grid(row=0, column=0, sticky="ew")
        self.grid_propagate(False)
        self.after_idle(self._reserve_height)
        self.bind("<<ThemeChanged>>", self._theme_changed)
        self._show_mode()

        for variable in (
            *self.straightness_variables.values(),
            *(var for group in self.classification_variables.values() for var in group.values()),
        ):
            variable.trace_add("write", self._changed)

    def _build_straightness(self):
        ttk.Label(self.straightness, text="Finger", width=16, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(self.straightness, text="Straightness", anchor="w").grid(
            row=0, column=1, sticky="w", pady=(0, 4)
        )
        for row, name in enumerate(FINGER_NAMES, start=1):
            ttk.Label(self.straightness, text=name.title(), width=16, anchor="w").grid(
                row=row, column=0, sticky="w", pady=4
            )
            variable = tk.StringVar(self, value="Any position")
            ttk.Combobox(
                self.straightness, textvariable=variable,
                values=tuple(STRAIGHTNESS_OPTIONS), state="readonly", width=24,
            ).grid(row=row, column=1, sticky="w", pady=4)
            self.straightness_variables[name] = variable

    def _build_classifications(self):
        ttk.Label(self.classifications, text="Finger", width=12, anchor="w").grid(
            row=0, column=0, sticky="w", padx=(0, 4)
        )
        for column, position in enumerate(FINGER_OPTIONS, start=1):
            ttk.Label(
                self.classifications, text=position.replace("_", " ").title(),
                anchor="center",
            ).grid(row=0, column=column, sticky="ew", padx=3)
            self.classifications.columnconfigure(column, weight=1, uniform="position")
        for row, name in enumerate(FINGER_NAMES, start=1):
            ttk.Label(self.classifications, text=name.title(), width=12, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(0, 6), pady=5
            )
            self.classification_variables[name] = {}
            for column, position in enumerate(FINGER_OPTIONS, start=1):
                variable = tk.BooleanVar(self)
                ttk.Checkbutton(self.classifications, variable=variable).grid(
                    row=row, column=column, padx=4, pady=5
                )
                self.classification_variables[name][position] = variable

    @property
    def mode(self):
        return self._mode

    def values(self):
        if self._mode == "classifications":
            return {
                name: frozenset(position for position, variable in variables.items() if variable.get())
                for name, variables in self.classification_variables.items()
            }
        return {
            name: (
                self._selections.get(name, frozenset())
                if variable.get() == CUSTOM_CLASSIFICATIONS
                else STRAIGHTNESS_OPTIONS[variable.get()]
            )
            for name, variable in self.straightness_variables.items()
        }

    def load(self, fingers):
        self._loading = True
        try:
            self._selections = {
                name: frozenset(fingers.get(name, ())) for name in FINGER_NAMES
            }
            for name, selected in self._selections.items():
                for position, variable in self.classification_variables[name].items():
                    variable.set(position in selected)
                label = next(
                    (label for label, choices in STRAIGHTNESS_OPTIONS.items() if choices == selected),
                    CUSTOM_CLASSIFICATIONS,
                )
                self.straightness_variables[name].set(label)
        finally:
            self._loading = False

    def _changed(self, *_args):
        if self._loading:
            return
        self.load(self.values())
        if self._on_change:
            self._on_change()

    def toggle_mode(self):
        self.load(self.values())
        self._mode = (
            "classifications" if self._mode == "straightness" else "straightness"
        )
        self._show_mode()

    def _show_mode(self):
        if self._mode == "straightness":
            self.classifications.grid_remove()
            self.straightness.grid()
        else:
            self.straightness.grid_remove()
            self.classifications.grid()

    def _reserve_height(self):
        height = max(self.straightness.winfo_reqheight(), self.classifications.winfo_reqheight()) + 4
        self.configure(height=height)

    def _theme_changed(self, _event):
        self.after_idle(self._reserve_height)
