"""Style destructive actions using the active application theme."""

from tkinter import ttk

from ..theme import ThemeColors


class DestructiveButtonStyle:
    STYLE_NAME = "Destructive.TButton"

    def __init__(self, root, colors=None):
        self.root = root
        self.colors = colors if colors is not None else ThemeColors(root)
        self._snapshot = None

    @classmethod
    def for_widget(cls, widget):
        """Share one style provider across windows in the same Tk interpreter."""
        root = widget._root()
        provider = getattr(root, "_destructive_button_style", None)
        if provider is None:
            provider = cls(root)
            root._destructive_button_style = provider
        return provider

    def apply(self):
        style = ttk.Style(self.root)
        foreground = self.colors.destructive
        disabled = (
            style.lookup("TButton", "foreground", ("disabled",))
            or style.lookup("TLabel", "foreground", ("disabled",))
            or foreground
        )
        snapshot = (style.theme_use(), foreground, disabled)
        if snapshot != self._snapshot:
            # Configuring styles can emit ThemeChanged. Cache first to avoid
            # repeated styling when every discard button receives that event.
            self._snapshot = snapshot
            style.configure(self.STYLE_NAME, foreground=foreground)
            style.map(
                self.STYLE_NAME,
                foreground=[("disabled", disabled), ("!disabled", foreground)],
            )
        # Layout, padding, typography, and background inherit from TButton.
        return self.STYLE_NAME
