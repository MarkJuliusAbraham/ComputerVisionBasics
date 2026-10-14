"""A focused card for the selected gesture's hand criteria."""

from tkinter import ttk

from hand_tracking.frontend.core.scaled_layout import ScaledLayout

from .hand_criteria import HandCriteriaSection


class GestureSection(ttk.LabelFrame):
    def __init__(self, master, appearance, on_change=None, segment_count=4):
        super().__init__(master, text="Hand criteria")
        ScaledLayout(self, appearance).configure(self, padding=16)
        self.criteria = HandCriteriaSection(
            self, on_change=on_change, appearance=appearance,
            segment_count=segment_count, show_heading=False,
        )
        self.criteria.pack(fill="x")
