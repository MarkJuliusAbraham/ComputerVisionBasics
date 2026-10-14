"""Selected gesture details independent of profile and list navigation."""

from tkinter import ttk

from hand_tracking.ui.core.scaled_layout import ScaledLayout

from ..gesture_draft import GestureDraft
from .command_sequence import CommandSequenceSection
from .gesture import GestureSection
from .gesture_heading import GestureHeading
from .tracking import GestureTrackingSection
from .repeat_commands import RepeatCommandsSection


class GestureEditorSection(ttk.Frame):
    def __init__(self, master, appearance, on_change=None, segment_count=4, *, on_repeat_change=None):
        super().__init__(master)
        self.appearance = appearance
        self.layout = ScaledLayout(self, appearance)
        self.heading = self.layout.pack(GestureHeading(self, appearance), fill="x", pady=(0, 14))
        self.name = self.heading.name
        self.criteria_card = self.layout.pack(
            GestureSection(self, appearance, on_change, segment_count), fill="x", pady=(0, 18),
        )
        self.tracking = self.layout.pack(
            GestureTrackingSection(self, on_change=on_change, appearance=appearance), fill="x", pady=(0, 18),
        )
        self.sequence = self.layout.pack(
            CommandSequenceSection(self, on_change=on_change, appearance=appearance), fill="x", pady=(0, 18),
        )
        self.repeats = self.layout.pack(
            RepeatCommandsSection(self, appearance, on_change=on_repeat_change), fill="x",
        )
        self.sections = (self.heading, self.criteria_card, self.tracking, self.sequence, self.repeats)
        self.empty = ttk.Label(
            self, text="No gestures in this profile. Use Manage gestures to create one.",
            wraplength=500,
        )
        self.layout.pack(self.empty, anchor="w", pady=16)
        self.empty.pack_forget()

    @property
    def segment_count(self):
        return self.criteria_card.criteria.fingers.segment_count

    def set_segment_count(self, count):
        self.criteria_card.criteria.set_segment_count(count)

    def show_gesture(self, name):
        self.name.set(name or "")
        if name is None:
            for widget in self.sections:
                widget.pack_forget()
            self.layout.show(self.empty)
        else:
            self.empty.pack_forget()
            if not self.heading.winfo_manager():
                self.layout.show(*self.sections)

    def show_conflict(self, conflict, names):
        self.heading.show_conflict(conflict, names)

    def load(self, draft):
        self.criteria_card.criteria.load(draft.criteria)
        self.sequence.load(draft.commands, draft.delay)
        self.tracking.load(draft.tracking, use_optimistic_tracking=draft.use_optimistic_tracking)
        self.repeats.load(draft.repeat)

    def values(self):
        return GestureDraft(
            criteria=self.criteria_card.criteria.values(),
            commands=self.sequence.commands.get(), delay=self.sequence.delay.get(),
            tracking=self.tracking.values(),
            repeat=self.repeats.values(),
            use_optimistic_tracking=self.tracking.optimistic_enabled.get(),
        )
