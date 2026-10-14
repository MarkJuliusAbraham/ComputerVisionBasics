"""Style destructive actions using the active application theme."""

from tkinter import ttk

from hand_tracking.ui.core.widget_tree import root_service

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
        return root_service(widget, "_destructive_button_style", cls)

    def apply(self):
        style = ttk.Style(self.root)
        palette = self.colors.destructive
        disabled_foreground = (
            style.lookup("TButton", "foreground", ("disabled",))
            or style.lookup("TLabel", "foreground", ("disabled",))
            or palette.foreground
        )
        disabled_background = (
            style.lookup("TButton", "background", ("disabled",))
            or style.lookup("TFrame", "background")
            or palette.background
        )
        disabled_border = (
            style.lookup("TButton", "bordercolor", ("disabled",))
            or palette.edges.outline
        )
        snapshot = (
            style.theme_use(), palette, disabled_foreground, disabled_background, disabled_border,
        )
        if snapshot != self._snapshot:
            # Configuring styles can emit ThemeChanged. Cache first to avoid
            # repeated styling when every discard button receives that event.
            self._snapshot = snapshot
            style.configure(
                self.STYLE_NAME, background=palette.background, foreground=palette.foreground,
                bordercolor=palette.edges.outline, lightcolor=palette.edges.highlight,
                darkcolor=palette.edges.shadow, focuscolor=palette.foreground, relief="raised",
            )
            style.map(
                self.STYLE_NAME,
                background=[("disabled", disabled_background), ("pressed", palette.pressed),
                            ("active", palette.hover), ("!disabled", palette.background)],
                foreground=[("disabled", disabled_foreground), ("!disabled", palette.foreground)],
                bordercolor=[("disabled", disabled_border), ("focus", palette.foreground),
                             ("!disabled", palette.edges.outline)],
                lightcolor=[("disabled", disabled_border), ("!disabled", palette.edges.highlight)],
                darkcolor=[("disabled", disabled_border), ("!disabled", palette.edges.shadow)],
                relief=[("disabled", "solid"), ("pressed", "sunken")],
            )
        # Layout, padding, and typography inherit from the shared button theme.
        return self.STYLE_NAME
