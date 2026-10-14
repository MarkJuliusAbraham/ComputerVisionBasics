"""A reusable discard action that retains normal ttk button behavior."""

from tkinter import ttk
from hand_tracking.frontend.core.idle_refresh import IdleRefresh

from .destructive_button_style import DestructiveButtonStyle


class DiscardChangesButton(ttk.Button):
    def __init__(
        self, master, *, command=None, text="Discard changes", style_provider=None, **kwargs,
    ):
        self._style_provider = (
            style_provider if style_provider is not None else DestructiveButtonStyle.for_widget(master)
        )
        super().__init__(
            master, text=text, command=command, style=self._style_provider.apply(), **kwargs,
        )
        self.theme_refresh = IdleRefresh(self, self._refresh_style, event="<<ThemeChanged>>")

    def _refresh_style(self):
        style_name = self._style_provider.apply()
        if self.cget("style") != style_name:
            self.configure(style=style_name)
