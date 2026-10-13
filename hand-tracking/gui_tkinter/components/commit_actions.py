"""Consistent commit/discard controls and a stable, wrapping status area."""

from tkinter import ttk

from gui_tkinter.core.idle_refresh import IdleRefresh

from .buttons import DiscardChangesButton
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
        self.discard_button = DiscardChangesButton(self, text=discard_label, command=on_discard)
        self.discard_button.pack(side="right")
        self.message = StatusMessage(self, appearance=self.appearance)
        self.message.pack(side="left", fill="x", expand=True)
        self.theme_refresh = IdleRefresh(self, self._refresh_layout, event="<<ThemeChanged>>")
        self._refresh_layout()
        self.set_dirty(False)

    def _refresh_layout(self):
        self.appearance.refresh()
        self.discard_button.pack_configure(padx=(0, self.appearance.pixels(10)))
        self.message.pack_configure(padx=(0, self.appearance.pixels(12)))

    def set_dirty(self, dirty):
        state = ["!disabled"] if dirty else ["disabled"]
        self.save_button.state(state)
        self.discard_button.state(state)

    def set_status(self, message, *, warning=False):
        self.message.set(message, warning=warning)
