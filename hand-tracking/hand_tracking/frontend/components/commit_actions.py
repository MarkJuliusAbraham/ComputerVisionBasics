"""Consistent commit/discard controls and a stable, wrapping status area."""

from tkinter import ttk

from hand_tracking.frontend.core.scaled_layout import ScaledLayout

from .buttons.discard_changes_button import DiscardChangesButton
from .status_message import StatusMessage
from .theme import ThemeMetrics


class CommitActions(ttk.Frame):
    def __init__(
        self, master, *, on_save, on_discard, save_label="Save changes",
        discard_label="Discard changes", appearance=None,
    ):
        super().__init__(master)
        self.appearance = appearance if appearance is not None else ThemeMetrics(self)
        self.save_button = ttk.Button(
            self, text=save_label, command=on_save, style="Accent.TButton",
        )
        self.save_button.pack(side="right")
        self.layout = ScaledLayout(self, self.appearance)
        self.discard_button = self.layout.pack(
            DiscardChangesButton(self, text=discard_label, command=on_discard), side="right", padx=(0, 10),
        )
        self.message = self.layout.pack(
            StatusMessage(self, appearance=self.appearance), side="left", fill="x", expand=True, padx=(0, 12),
        )
        self.set_dirty(False)

    def set_dirty(self, dirty):
        state = ["!disabled"] if dirty else ["disabled"]
        self.save_button.state(state)
        self.discard_button.state(state)

    def set_status(self, message, *, warning=False):
        self.message.set(message, warning=warning)
