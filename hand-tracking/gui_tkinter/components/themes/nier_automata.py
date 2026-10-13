"""Light and dark styling inspired by NieR:Automata's beige system menus.

References:
https://www.platinumgames.com/official-blog/article/9624
https://interfaceingame.com/screenshots/nierautomata-settings-dropdown/
https://interfaceingame.com/games/nierautomata/
"""

from tkinter import font as tkfont, ttk

from .checkbox_indicator import SquareCheckboxIndicator
from .choice_controls import ChoiceControlTheme


class NierAutomataTheme:
    """Share flat, square-edged ttk styling across light and dark palettes."""

    BODY_FONT = "NierBodyFont"
    HEADING_FONT = "NierHeadingFont"

    def __init__(
        self, root, *, name, palette,
        font_families=("Bahnschrift", "Segoe UI", "Arial"),
    ):
        self.root = root
        self.name = name
        self.palette = palette
        self.font_families = font_families

    def apply(self, scale, font_size):
        style = ttk.Style(self.root)
        if self.name not in style.theme_names():
            # Sun Valley paints controls with images that contain their own
            # colors. Clam's native elements accept our palette throughout.
            style.theme_create(self.name, parent="clam")
        self._configure_fonts(font_size)
        choices = ChoiceControlTheme(self.palette)
        size, margins = choices.indicator_geometry(scale)
        SquareCheckboxIndicator.for_theme(self.root, self.name).apply(
            self.palette, size=size, margins=margins, scale=scale,
        )
        # Configure the theme before selecting it, so widgets repaint with
        # the complete palette rather than briefly showing the parent theme.
        with_theme = {
            **self._surfaces(),
            **self._controls(),
            **choices.settings(scale),
            **self._navigation(scale),
            **self._lists(),
        }
        style.theme_settings(self.name, with_theme)
        style.theme_use(self.name)
        self._native_palette()

    def _configure_fonts(self, size):
        families = set(tkfont.families(self.root))
        fallback = tkfont.nametofont("TkDefaultFont", root=self.root).actual("family")
        family = next(
            (name for name in self.font_families if name in families),
            fallback,
        )
        existing = self.root.tk.splitlist(self.root.tk.call("font", "names"))
        for name, weight in ((self.BODY_FONT, "normal"), (self.HEADING_FONT, "bold")):
            command = "configure" if name in existing else "create"
            # Tcl owns these named fonts for the interpreter's lifetime.
            self.root.tk.call("font", command, name, "-family", family,
                              "-size", size, "-weight", weight)

    def _surfaces(self):
        p = self.palette
        return {
            ".": {
                "configure": {
                    "background": p.surface, "foreground": p.foreground,
                    "fieldbackground": p.field, "bordercolor": p.border,
                    "lightcolor": p.surface, "darkcolor": p.surface,
                    "troughcolor": p.track, "focuscolor": p.foreground,
                    "selectbackground": p.selection, "selectforeground": p.selection_text,
                    "selectborderwidth": 0, "font": self.BODY_FONT,
                },
                "map": {
                    "background": [("disabled", p.surface)],
                    "foreground": [("disabled", p.disabled)],
                    "selectbackground": [("!focus", p.selection)],
                    "selectforeground": [("!focus", p.selection_text)],
                },
            },
            "TFrame": {"configure": {"background": p.surface}},
            "TLabel": {"configure": {"background": p.surface, "foreground": p.foreground}},
            "TLabelframe": {"configure": {
                "background": p.surface, "bordercolor": p.border,
                "borderwidth": 1, "relief": "solid",
            }},
            "TLabelframe.Label": {"configure": {
                "background": p.surface, "foreground": p.foreground,
                "font": self.HEADING_FONT,
            }},
            "TSeparator": {"configure": {"background": p.border}},
        }

    def _controls(self):
        p = self.palette
        # Button styling is shared by ButtonTheme across all theme families.
        styles = {}
        for name in ("TEntry", "TCombobox", "TSpinbox"):
            styles[name] = {
                "configure": {
                    "fieldbackground": p.field, "background": p.panel,
                    "foreground": p.foreground, "arrowcolor": p.foreground,
                    "insertcolor": p.foreground, "borderwidth": 1,
                    "lightcolor": p.field, "darkcolor": p.field,
                },
                "map": {
                    "background": [("disabled", p.surface), ("active", p.hover),
                                   ("readonly", p.panel)],
                    "fieldbackground": [("disabled", p.surface), ("readonly", p.field)],
                    "foreground": [("disabled", p.disabled), ("readonly", p.foreground)],
                    "arrowcolor": [("disabled", p.disabled)],
                    "bordercolor": [("focus", p.foreground)],
                    "lightcolor": [("focus", p.field)],
                    "darkcolor": [("focus", p.field)],
                },
            }
        return styles

    def _navigation(self, scale):
        p = self.palette
        padding = (round(16 * scale), round(8 * scale))
        return {
            "TNotebook": {"configure": {
                "background": p.surface, "bordercolor": p.border, "borderwidth": 1,
            }},
            "TNotebook.Tab": {
                "configure": {"padding": padding, "background": p.hover,
                              "foreground": p.foreground, "font": self.BODY_FONT},
                "map": {
                    "padding": [],
                    "background": [("disabled", p.surface), ("selected", p.selection),
                                   ("active", p.panel)],
                    "foreground": [("disabled", p.disabled), ("selected", p.selection_text)],
                    "lightcolor": [("selected", p.selection), ("!selected", p.hover)],
                    "darkcolor": [("selected", p.selection), ("!selected", p.hover)],
                },
            },
            "TScrollbar": {
                "configure": {"background": p.hover, "troughcolor": p.surface,
                              "arrowcolor": p.foreground, "borderwidth": 0},
                "map": {"background": [("pressed", p.muted), ("active", p.border)]},
            },
        }

    def _lists(self):
        p = self.palette
        return {
            "Treeview": {
                "configure": {"background": p.field, "fieldbackground": p.field,
                              "foreground": p.foreground, "borderwidth": 1},
                "map": {
                    "background": [("disabled", p.surface), ("selected", p.selection)],
                    "foreground": [("disabled", p.disabled), ("selected", p.selection_text)],
                },
            },
            "Heading": {
                "configure": {"background": p.hover, "foreground": p.foreground,
                              "font": self.HEADING_FONT, "relief": "flat"},
                "map": {"background": [("active", p.hover)], "relief": [("pressed", "flat")]},
            },
        }

    def _native_palette(self):
        p = self.palette
        self.root.tk.call(
            "tk_setPalette", "background", p.surface, "foreground", p.foreground,
            "activeBackground", p.selection, "activeForeground", p.selection_text,
            "selectBackground", p.selection, "selectForeground", p.selection_text,
            "disabledForeground", p.disabled, "highlightColor", p.foreground,
        )
