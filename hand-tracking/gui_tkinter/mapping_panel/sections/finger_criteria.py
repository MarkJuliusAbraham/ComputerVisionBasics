"""Aligned finger criteria tables with interchangeable editing modes."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.theme import ThemeMetrics

from .criteria_options import (
    CUSTOM_CLASSIFICATIONS,
    FingerCriteriaOptions,
    FINGER_NAMES,
    FINGER_OPTIONS,
)


class FingerCriteriaEditor(ttk.Frame):
    """Synchronize both tables while preserving their size and row alignment."""

    def __init__(self, master, on_change=None, appearance=None, segment_count=4):
        super().__init__(master)
        self.appearance = appearance or ThemeMetrics(self)
        self._on_change = on_change
        self._loading = False
        self._mode = "straightness"
        self._selections = {}
        self.options = FingerCriteriaOptions(segment_count)
        self.availability_message = tk.StringVar(self)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.straightness = ttk.Frame(self)
        self.classifications = ttk.Frame(self)
        self.straightness_variables = {}
        self.straightness_controls = {}
        self.classification_variables = {}
        self._classification_controls = {}
        self._classification_headings = {}
        self._classification_dividers = []
        self._controls = []
        self._build_straightness()
        self._build_classifications()
        self.straightness.grid(row=0, column=0, sticky="nsew")
        self.classifications.grid(row=0, column=0, sticky="nsew")
        self.grid_propagate(False)
        self.after_idle(self._reserve_layout)
        self.bind("<<ThemeChanged>>", lambda _event: self.after_idle(self._reserve_layout))
        self._show_mode()

        for variable in (
            *self.straightness_variables.values(),
            *(var for group in self.classification_variables.values() for var in group.values()),
        ):
            variable.trace_add("write", self._changed)
        self.load({})

    @property
    def label_width(self):
        return self.appearance.font.measure("Palm orientation") + self.appearance.pixels(16)

    def _heading(self, page, text, column, center=False):
        label = ttk.Label(
            page, text=text, font=self.appearance.heading_font,
            anchor="center" if center else "w", justify="center" if center else "left",
        )
        label.grid(row=0, column=column, sticky="ew")
        return label

    def _finger_label(self, page, name, row, columns):
        ttk.Label(page, text=name.title(), anchor="w").grid(
            row=row, column=0, sticky="w"
        )
        if row < 2 * len(FINGER_NAMES):
            separator = ttk.Separator(page, orient="horizontal")
            separator.grid(row=row + 1, column=0, columnspan=columns, sticky="ew")
            return separator

    def _build_straightness(self):
        self._heading(self.straightness, "Finger", 0)
        self._heading(self.straightness, "Allowed position", 1)
        ttk.Separator(self.straightness, orient="horizontal").grid(
            row=1, column=0, columnspan=2, sticky="ew"
        )
        self.straightness.columnconfigure(1, weight=1)
        for index, name in enumerate(FINGER_NAMES):
            row = 2 * index + 2
            self._finger_label(self.straightness, name, row, 2)
            variable = tk.StringVar(self, value="Any position")
            combo = ttk.Combobox(
                self.straightness, textvariable=variable,
                values=tuple(self.options.simple_choices), state="readonly", width=1,
            )
            combo.grid(row=row, column=1, sticky="ew")
            self._controls.append(combo)
            self.straightness_variables[name] = variable
            self.straightness_controls[name] = combo

    def _build_classifications(self):
        self._heading(self.classifications, "Finger", 0)
        for column, position in enumerate(FINGER_OPTIONS, start=1):
            self._classification_headings[position] = self._heading(
                self.classifications, position.replace("_", "\n").title(),
                column, center=True,
            )
            self.classifications.columnconfigure(column, weight=1, uniform="position")
        divider = ttk.Separator(self.classifications, orient="horizontal")
        divider.grid(
            row=1, column=0, columnspan=len(FINGER_OPTIONS) + 1, sticky="ew",
        )
        self._classification_dividers.append(divider)
        for index, name in enumerate(FINGER_NAMES):
            row = 2 * index + 2
            divider = self._finger_label(
                self.classifications, name, row, len(FINGER_OPTIONS) + 1,
            )
            if divider is not None:
                self._classification_dividers.append(divider)
            self.classification_variables[name] = {}
            self._classification_controls[name] = {}
            for column, position in enumerate(FINGER_OPTIONS, start=1):
                variable = tk.BooleanVar(self)
                checkbox = ttk.Checkbutton(self.classifications, variable=variable)
                checkbox.grid(row=row, column=column)
                self._controls.append(checkbox)
                self.classification_variables[name][position] = variable
                self._classification_controls[name][position] = checkbox

    @property
    def mode(self):
        return self._mode

    @property
    def segment_count(self):
        return self.options.segment_count

    def set_segment_count(self, segment_count):
        selections = self.values()
        self.options = FingerCriteriaOptions(segment_count)
        self.load(selections)
        self._reserve_layout()

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
                else self.options.simple_choices[variable.get()]
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
                    (label for label, choices in self.options.simple_choices.items() if choices == selected),
                    CUSTOM_CLASSIFICATIONS,
                )
                labels = tuple(self.options.simple_choices)
                if label == CUSTOM_CLASSIFICATIONS:
                    labels += (CUSTOM_CLASSIFICATIONS,)
                self.straightness_controls[name].configure(values=labels)
                self.straightness_variables[name].set(label)
        finally:
            self._loading = False
        self._refresh_classifications()

    def _refresh_classifications(self):
        inactive = self.options.inactive_selections(self._selections)
        self._visible_positions = tuple(
            position for position in FINGER_OPTIONS
            if position in self.options.positions or position in inactive
        )
        for column in range(1, len(FINGER_OPTIONS) + 1):
            self.classifications.columnconfigure(column, minsize=0, weight=0, uniform="")
        for position, heading in self._classification_headings.items():
            heading.grid_remove()
            for controls in self._classification_controls.values():
                controls[position].grid_remove()
        for column, position in enumerate(self._visible_positions, start=1):
            active = position in self.options.positions
            heading = self._classification_headings[position]
            heading.configure(
                text=position.replace("_", "\n").title() + ("" if active else "\n(inactive)"),
            )
            heading.state(["!disabled"] if active else ["disabled"])
            heading.grid(row=0, column=column, sticky="ew")
            self.classifications.columnconfigure(column, weight=1, uniform="position")
            for name, controls in self._classification_controls.items():
                checkbox = controls[position]
                checkbox.grid(column=column)
                checkbox.state(
                    ["!disabled"] if active or self.classification_variables[name][position].get()
                    else ["disabled"]
                )
        for divider in self._classification_dividers:
            divider.grid_configure(columnspan=len(self._visible_positions) + 1)
        names = ", ".join(
            position.replace("_", " ") for position in FINGER_OPTIONS if position in inactive
        )
        self.availability_message.set(
            f"{self.segment_count} segments. Saved classification selections are retained.\n"
            + (f"Inactive: {names}. These cannot be detected at this segment count."
               if inactive else "All selected classifications are available.")
        )

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

    def _reserve_layout(self):
        self.appearance.refresh()
        spacing = self.appearance.pixels(12)
        header_height = 3 * self.appearance.font.metrics("linespace") + spacing
        row_height = max(control.winfo_reqheight() for control in self._controls) + spacing
        separator_height = max(2, self.appearance.pixels(1))
        simple_width = max(
            self.appearance.font.measure(label)
            for label in (*self.options.simple_choices, CUSTOM_CLASSIFICATIONS)
        ) + self.appearance.pixels(44)
        heading_words = ["(inactive)"] + [
            word for position in FINGER_OPTIONS
            for word in position.replace("_", " ").title().split()
        ]
        class_width = max(
            self.appearance.heading_font.measure(word) for word in heading_words
        ) + self.appearance.pixels(16)

        for page in (self.straightness, self.classifications):
            page.columnconfigure(0, minsize=self.label_width)
            page.rowconfigure(0, minsize=header_height)
            for index in range(len(FINGER_NAMES)):
                page.rowconfigure(2 * index + 2, minsize=row_height, uniform="finger")
                page.rowconfigure(2 * index + 1, minsize=separator_height)
        self.straightness.columnconfigure(1, minsize=simple_width)
        for column in range(1, len(self._visible_positions) + 1):
            self.classifications.columnconfigure(column, minsize=class_width)
        self.configure(
            width=self.label_width + max(simple_width, len(FINGER_OPTIONS) * class_width),
            height=header_height + len(FINGER_NAMES) * (row_height + separator_height),
        )
