"""Gesture selection and its hand criteria."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.theme import ThemeMetrics

from ..display_names import gesture_display_names
from .hand_criteria import HandCriteriaSection


class GestureSection(ttk.LabelFrame):
    """Select a gesture and edit its criteria within one consistent section."""

    def __init__(
        self, master, on_select=None, on_manage=None, on_change=None, segment_count=4,
    ):
        super().__init__(master, text="Gesture")
        self.appearance = ThemeMetrics(self)
        self._on_select = on_select
        self._labels_to_ids = {}
        self.columnconfigure(0, weight=1)
        self.selected = tk.StringVar(self)

        self.selection_row = ttk.Frame(self)
        self.selection_row.grid(row=0, column=0, sticky="ew")
        self.selection_row.columnconfigure(0, weight=1)
        self.selection_label = ttk.Label(
            self.selection_row, text="Selected gesture",
            font=self.appearance.heading_font,
        )
        self.selection_label.grid(row=0, column=0, columnspan=2, sticky="w")
        self.selector = ttk.Combobox(
            self.selection_row, textvariable=self.selected, state="readonly", width=1,
        )
        self.selector.grid(row=1, column=0, sticky="ew")
        self.selector.bind("<<ComboboxSelected>>", self._selection_changed)
        manage_button = ttk.Button(
            self.selection_row, text="Manage gestures", command=on_manage, width=18,
        )
        manage_button.grid(row=1, column=1)
        if on_manage is None:
            manage_button.state(["disabled"])

        self.divider = ttk.Separator(self, orient="horizontal")
        self.divider.grid(row=1, column=0, sticky="ew")
        self.criteria = HandCriteriaSection(
            self, on_change=on_change, appearance=self.appearance,
            segment_count=segment_count,
        )
        self.criteria.grid(row=2, column=0, sticky="ew")
        self._refresh_layout()
        self.bind("<<ThemeChanged>>", lambda _event: self.after_idle(self._refresh_layout))

    def _refresh_layout(self):
        self.appearance.refresh()
        gap = self.appearance.pixels(12)
        self.configure(padding=self.appearance.pixels(16))
        self.selection_row.grid_configure(pady=(0, gap))
        self.selection_label.grid_configure(pady=(0, gap // 2))
        self.selector.grid_configure(padx=(0, gap))
        self.divider.grid_configure(pady=(0, gap))

    def load_choices(self, definitions, selected_id=None):
        self._labels_to_ids = {
            label: definition.id for definition, label in gesture_display_names(definitions)
        }
        self.selector.configure(
            values=tuple(self._labels_to_ids),
            state="readonly" if self._labels_to_ids else "disabled",
        )
        label = next(
            (label for label, gesture_id in self._labels_to_ids.items() if gesture_id == selected_id),
            "",
        )
        self.selected.set(label)

    def _selection_changed(self, _event):
        gesture_id = self._labels_to_ids.get(self.selected.get())
        if gesture_id is not None and self._on_select:
            self._on_select(gesture_id)
