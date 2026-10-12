"""Scrollable mapping form assembled from independent widget sections."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.scrollable_frame import ScrollableFrame

from .gesture_draft import GestureDraft
from .sections import CommandSequenceSection, GestureSection, ProfileSection


class MappingForm(ttk.Frame):
    """Own form layout and translate section values into one gesture draft."""

    def __init__(
        self, master, *, on_change=None, on_select=None, on_manage=None,
        on_choose_profile=None, on_save=None,
    ):
        super().__init__(master, padding=(24, 20))
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(
            header, text="Gesture mappings", font=("TkDefaultFont", 12, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Choose the hand criteria that trigger each command. Rules must not overlap.",
            wraplength=660,
        ).pack(anchor="w", pady=(6, 0))

        # Reserve the footer first so lengthy criteria never push Save offscreen.
        footer = ttk.Frame(self)
        footer.pack(side="bottom", fill="x", pady=(12, 0))
        self.status = tk.StringVar(self, value="Gesture mappings loaded")
        ttk.Label(footer, textvariable=self.status, wraplength=500).pack(
            side="left", fill="x", expand=True
        )
        self.save_button = ttk.Button(
            footer, text="Save mappings", command=on_save, style="Accent.TButton",
        )
        self.save_button.pack(side="right")

        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        group = ttk.LabelFrame(self.scroll.content, text="Gesture Profile", padding=14)
        group.pack(fill="x", pady=(0, 14))
        self.profile = ProfileSection(group, on_choose=on_choose_profile)
        self.profile.pack(fill="x")
        ttk.Separator(group, orient="horizontal").pack(fill="x", pady=(12, 14))
        self.gesture = GestureSection(
            group, on_select=on_select, on_manage=on_manage, on_change=on_change,
        )
        self.gesture.pack(fill="x", pady=(0, 12))
        self.sequence = CommandSequenceSection(group, on_change=on_change)
        self.sequence.pack(fill="x")

    def values(self):
        return GestureDraft(
            criteria=self.gesture.criteria.values(),
            commands=self.sequence.commands.get(),
            delay=self.sequence.delay.get(),
        )

    def load_draft(self, draft):
        self.gesture.criteria.load(draft.criteria)
        self.sequence.load(draft.commands, draft.delay)

    def show_profile(self, path):
        self.profile.load(path)

    def show_gestures(self, definitions, selected_id):
        self.gesture.load_choices(definitions, selected_id)

    def set_dirty(self, dirty):
        self.save_button.state(["!disabled"] if dirty else ["disabled"])

    def set_status(self, message):
        self.status.set(message)
