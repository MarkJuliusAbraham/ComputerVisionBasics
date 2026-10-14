"""Edit the profile's universal reset rule using the shared criteria component."""

from tkinter import ttk

from .hand_criteria import HandCriteriaSection


class ResetGestureSection(ttk.LabelFrame):
    """A reset has hand criteria and a built-in action, with no command sequence."""

    def __init__(self, master, on_change=None, segment_count=4):
        super().__init__(master, text="Universal reset", padding=16)
        ttk.Label(
            self,
            text="Stops queued commands, clears the drawing, and re-arms gesture input.",
            wraplength=650,
        ).pack(anchor="w")
        ttk.Label(
            self,
            text="Applies to every gesture in this profile and takes precedence over command rules.",
            wraplength=650,
        ).pack(anchor="w", pady=(6, 12))
        self.criteria = HandCriteriaSection(
            self, on_change=on_change, segment_count=segment_count,
        )
        self.criteria.pack(fill="x")

    def values(self):
        return self.criteria.values()

    def load(self, match):
        self.criteria.load(match)

    def set_segment_count(self, segment_count):
        self.criteria.set_segment_count(segment_count)
