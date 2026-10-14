import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont
from tkinter import ttk

from hand_tracking.settings.theme_choices import resolve_theme

from .themes.buttons import ButtonTheme
from .themes.nier_automata import NierAutomataTheme
from .themes.palettes import PALETTES, ClassificationPalette
from .themes.popups import PopupTheme
from .themes.scaling import scale_pixels
from .themes.title_bar import TitleBarPalette, TitleBarTheme
from .themes.typography import ThemeTypography

try:
    import sv_ttk
except ImportError:  # Keep the restored Tk route usable without an optional theme package.
    sv_ttk = None

BASE_FONT_SIZE = 9            # points at 100%
BASE_BUTTON_PADDING = (8, 3)  # pixels at 100%

_SV_FONTS = ("SunValleyBodyFont", "SunValleyCaptionFont", "SunValleyBodyStrongFont")

_system_scale = None


@dataclass(frozen=True)
class AlertPalette:
    foreground: str
    selection_background: str


@dataclass(frozen=True)
class OverlayTextPalette:
    """Keep dark overlay lettering readable when its pale surface fades."""

    outline: str | None


class ThemeColors:
    """Semantic UI colors resolved from the currently painted theme."""

    def __init__(self, widget):
        self.widget = widget

    @property
    def choice(self):
        return resolve_theme(ttk.Style(self.widget).theme_use())

    @property
    def palette(self):
        return PALETTES[self.choice.name]

    @property
    def high_alert(self):
        palette = self.palette
        return AlertPalette(palette.alert, palette.alert_surface)

    @property
    def destructive(self):
        """Filled destructive action colors, separate from warning text."""
        return self.palette.destructive

    @property
    def overlay_text(self) -> OverlayTextPalette:
        return OverlayTextPalette(None if self.choice.dark else self.palette.panel)

    @property
    def title_bar(self):
        style = ttk.Style(self.widget)
        palette = self.palette
        return TitleBarPalette(
            background=style.lookup("TFrame", "background") or palette.surface,
            foreground=style.lookup("TLabel", "foreground") or palette.foreground,
            border=palette.border,
            dark=self.choice.dark,
        )


class ThemeMetrics:
    """Share the active theme's typography and scaled spacing within a form."""

    def __init__(self, widget):
        self.widget = widget
        self.colors = ThemeColors(widget)
        self.font = tkfont.Font(root=widget)
        self.heading_font = self.font.copy()
        self._variants = []
        self.refresh()

    def font_variant(self, *, size_delta=0, weight=None):
        """Keep a component's emphasis in sync with the theme's font family."""
        variant = self.font.copy()
        self._variants.append((variant, size_delta, weight))
        self.refresh()
        return variant

    def refresh(self):
        self.scale = float(self.widget.tk.call("tk", "scaling")) * 72 / 96
        font_name = ttk.Style(self.widget).lookup("TLabel", "font") or "TkDefaultFont"
        actual = self.widget.tk.splitlist(self.widget.tk.call("font", "actual", font_name))
        attributes = {
            str(key).lstrip("-"): value for key, value in zip(actual[::2], actual[1::2])
        }
        for key in ("size", "underline", "overstrike"):
            attributes[key] = int(attributes[key])
        if self.font.actual() != attributes:
            self.font.configure(**attributes)
        heading_attributes = {**attributes, "weight": "bold"}
        if self.heading_font.actual() != heading_attributes:
            self.heading_font.configure(**heading_attributes)
        for variant, size_delta, weight in self._variants:
            variant_attributes = {
                **attributes, "size": attributes["size"] + size_delta,
                "weight": weight if weight is not None else attributes["weight"],
            }
            if variant.actual() != variant_attributes:
                variant.configure(**variant_attributes)

    def pixels(self, value):
        return scale_pixels(value, self.scale)


def system_scale(root):
    """Windows' display scale (1.0 = 100%). Read once, before we change Tk's own scaling."""
    global _system_scale
    if _system_scale is None:
        _system_scale = root.winfo_fpixels("1i") / 96
    return _system_scale


def resolve_scale(root, value):
    """Turn a setting value like 'Auto' or '150%' into a scale factor."""
    system = system_scale(root)  # always read first, so Auto never sees our own change
    if value == "Auto":
        return system
    return int(value.rstrip("%")) / 100


@dataclass(frozen=True)
class DeviationPalette:
    """Colors shared by live bars, editable bands, handles, and legends.

    The theme's classification colors are resolved once, when the palette is
    created, rather than on every bar and label update.
    """

    theme_name: str
    surface: str
    track: str
    foreground: str
    classes: ClassificationPalette

    def classification(self, category):
        """The bar color for a finger classification."""
        return self.classes.color(category).fill

    def classification_text(self, category):
        """A readable shade of the bar's color for small classification text."""
        return self.classes.color(category).text


class DeviationTheme:
    """Resolve canvas colors from the application theme and active ttk styles."""

    def __init__(self, widget):
        self.widget = widget

    def palette(self, theme_name):
        style = ttk.Style(self.widget)
        # ThemeChanged may arrive before panels receive the updated settings.
        # Read the painted theme so cached panel names cannot restore old colors.
        theme_name = resolve_theme(style.theme_use()).name
        palette = PALETTES[theme_name]
        surface = style.lookup("TFrame", "background") or palette.surface
        foreground = style.lookup("TLabel", "foreground") or palette.foreground
        return DeviationPalette(theme_name, surface, palette.track, foreground, palette.deviation)


def apply_theme(root, name, scale=1.0):
    """Apply the named theme at the given scale. Safe to call at any time."""
    # Tk scaling is pixels per point: 96/72 at 100%.
    root.tk.call("tk", "scaling", scale * 96 / 72)

    choice = resolve_theme(name)
    if choice.family == "standard" and sv_ttk is not None:
        sv_ttk.set_theme("dark" if choice.dark else "light", root=root)
        # Sun Valley sets this through a queued ThemeChanged callback. Set
        # its font now so newly built panels read the correct typography.
        ttk.Style(root).configure(".", font="SunValleyBodyFont")
    else:
        families = (
            ("Bahnschrift", "Segoe UI", "Arial") if choice.family == "nier"
            else ("Segoe UI", "Arial")
        )
        NierAutomataTheme(
            root, name=choice.style_name, palette=PALETTES[choice.name],
            font_families=families,
        ).apply(scale, BASE_FONT_SIZE)

    for font_name in _SV_FONTS:
        try:
            tkfont.nametofont(font_name, root=root).configure(size=BASE_FONT_SIZE)
        except tk.TclError:
            pass  # that font name doesn't exist in this sv-ttk version

    padding = tuple(scale_pixels(value, scale) for value in BASE_BUTTON_PADDING)
    style = ttk.Style(root)
    combo_font = style.lookup("TLabel", "font") or "TkDefaultFont"
    style.configure("TCombobox", font=combo_font)
    ThemeTypography(root, combo_font).apply()
    ButtonTheme(
        root, PALETTES[choice.name], minimum_width=0 if choice.family == "nier" else None,
    ).apply()
    PopupTheme.for_root(root).apply(PALETTES[choice.name], combo_font)
    style.configure("TButton", padding=padding)
    style.configure("Accent.TButton", padding=padding)
    TitleBarTheme.for_root(root, lambda: ThemeColors(root).title_bar).refresh()
