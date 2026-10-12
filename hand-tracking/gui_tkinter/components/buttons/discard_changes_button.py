"""A reusable discard action that retains normal ttk button behavior."""

from tkinter import ttk

from .destructive_button_style import DestructiveButtonStyle


class DiscardChangesButton(ttk.Button):
    def __init__(
        self, master, *, command=None, text="Discard changes", style_provider=None, **kwargs,
    ):
        self._style_provider = (
            style_provider if style_provider is not None else DestructiveButtonStyle.for_widget(master)
        )
        self._theme_update = None
        super().__init__(
            master, text=text, command=command, style=self._style_provider.apply(), **kwargs,
        )
        self.bind("<<ThemeChanged>>", self._theme_changed, add="+")
        self.bind("<Destroy>", self._destroyed, add="+")

    def _theme_changed(self, _event):
        if self._theme_update is None:
            self._theme_update = self.after_idle(self._refresh_style)

    def _refresh_style(self):
        self._theme_update = None
        style_name = self._style_provider.apply()
        if self.cget("style") != style_name:
            self.configure(style=style_name)

    def _destroyed(self, event):
        if event.widget is self and self._theme_update is not None:
            self.after_cancel(self._theme_update)
            self._theme_update = None
