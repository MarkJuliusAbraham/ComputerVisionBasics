"""Gesture selection and its hand criteria."""

import tkinter as tk
from tkinter import ttk

from ..display_names import gesture_display_names
from .hand_criteria import HandCriteriaSection


class GestureSection(ttk.LabelFrame):
    """Translate user-facing gesture labels to stable definition IDs."""

    def __init__(self, master, on_select=None, on_manage=None, on_change=None):
        super().__init__(master, text="Gesture", padding=14)
        self._on_select = on_select
        self._labels_to_ids = {}
        self.selected = tk.StringVar(self)
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(0, 14))
        ttk.Label(row, text="Gesture").pack(side="left", padx=(0, 8))
        self.selector = ttk.Combobox(
            row, textvariable=self.selected, state="readonly", width=24,
        )
        self.selector.pack(side="left")
        self.selector.bind("<<ComboboxSelected>>", self._selection_changed)
        ttk.Button(row, text="Manage Gestures", command=on_manage).pack(side="right")
        self.criteria = HandCriteriaSection(self, on_change=on_change)
        self.criteria.pack(fill="x")

    def load_choices(self, definitions, selected_id=None):
        self._labels_to_ids = {
            label: definition.id for definition, label in gesture_display_names(definitions)
        }
        self.selector.configure(values=tuple(self._labels_to_ids))
        label = next(
            (label for label, gesture_id in self._labels_to_ids.items() if gesture_id == selected_id),
            "",
        )
        self.selected.set(label)

    def _selection_changed(self, _event):
        gesture_id = self._labels_to_ids.get(self.selected.get())
        if gesture_id is not None and self._on_select:
            self._on_select(gesture_id)
