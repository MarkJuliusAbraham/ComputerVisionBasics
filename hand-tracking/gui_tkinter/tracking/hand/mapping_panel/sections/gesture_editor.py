"""Selected gesture details independent of profile and list navigation."""

from tkinter import ttk

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
        self.heading = GestureHeading(self, appearance)
        self.name = self.heading.name
        self.heading.pack(fill="x", pady=(0, appearance.pixels(14)))
        self.criteria_card = GestureSection(self, appearance, on_change, segment_count)
        self.criteria_card.pack(fill="x", pady=(0, appearance.pixels(18)))
        self.tracking = GestureTrackingSection(self, on_change=on_change, appearance=appearance)
        self.tracking.pack(fill="x", pady=(0, appearance.pixels(18)))
        self.sequence = CommandSequenceSection(self, on_change=on_change, appearance=appearance)
        self.sequence.pack(fill="x", pady=(0, appearance.pixels(18)))
        self.repeats = RepeatCommandsSection(self, appearance, on_change=on_repeat_change)
        self.repeats.pack(fill="x")
        self.empty = ttk.Label(
            self, text="No gestures in this profile. Use Manage gestures to create one.",
            wraplength=500,
        )
        self.bind("<<ThemeChanged>>", lambda _event: self.after_idle(self._refresh_layout))

    def _refresh_layout(self):
        self.appearance.refresh()
        pixels = self.appearance.pixels
        self.criteria_card.configure(padding=pixels(16))
        if self.heading.winfo_manager():
            self.heading.pack_configure(pady=(0, pixels(14)))
            self.criteria_card.pack_configure(pady=(0, pixels(18)))
            self.tracking.pack_configure(pady=(0, pixels(18)))
            self.sequence.pack_configure(pady=(0, pixels(18)))

    @property
    def segment_count(self):
        return self.criteria_card.criteria.fingers.segment_count

    def set_segment_count(self, count):
        self.criteria_card.criteria.set_segment_count(count)

    def show_gesture(self, name):
        self.name.set(name or "")
        if name is None:
            for widget in (self.heading, self.criteria_card, self.tracking, self.sequence, self.repeats):
                widget.pack_forget()
            self.empty.pack(anchor="w", pady=self.appearance.pixels(16))
        else:
            self.empty.pack_forget()
            if not self.heading.winfo_manager():
                self.heading.pack(fill="x", pady=(0, self.appearance.pixels(14)))
                self.criteria_card.pack(fill="x", pady=(0, self.appearance.pixels(18)))
                self.tracking.pack(fill="x", pady=(0, self.appearance.pixels(18)))
                self.sequence.pack(fill="x", pady=(0, self.appearance.pixels(18)))
                self.repeats.pack(fill="x")

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
