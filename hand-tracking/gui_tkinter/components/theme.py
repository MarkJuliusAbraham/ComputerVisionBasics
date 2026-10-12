import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont
from tkinter import ttk

try:
    import sv_ttk
except ImportError:  # Keep the restored Tk route usable without an optional theme package.
    sv_ttk = None

# Our setting values -> sv-ttk's names
_MODES = {"Light": "light", "Dark": "dark"}

# Semantic gesture colors are defined with the app theme so labels stay readable
# on both theme backgrounds. Widgets request these styles by classification.
_GESTURE_COLORS = {
    "Light": {
        "straight": "#1e7e34",
        "partial": "#8a6100",
        "curled": "#b54708",
        "very_curled": "#9950a8",
        "nearly_closed": "#b83273",
        "closed": "#c5221f",
    },
    "Dark": {
        "straight": "#81c995",
        "partial": "#fdd663",
        "curled": "#ffb77c",
        "very_curled": "#c8a0e8",
        "nearly_closed": "#f39ac5",
        "closed": "#f28b82",
    },
}
_GESTURE_BAR_BACKGROUNDS = {"Light": "#e5e7eb", "Dark": "#343a43"}
_TEXT_COLORS = {"Light": "#202020", "Dark": "#f4f4f4"}

BASE_FONT_SIZE = 9            # points at 100%
BASE_BUTTON_PADDING = (8, 3)  # pixels at 100%

_SV_FONTS = ("SunValleyBodyFont", "SunValleyCaptionFont", "SunValleyBodyStrongFont")

_system_scale = None


@dataclass(frozen=True)
class AlertPalette:
    foreground: str
    selection_background: str


class ThemeColors:
    """Semantic UI colors resolved from the currently painted theme."""

    HIGH_ALERT = {
        "Light": AlertPalette("#b42318", "#fee4e2"),
        "Dark": AlertPalette("#ff9b94", "#532422"),
    }

    def __init__(self, widget):
        self.widget = widget

    @property
    def high_alert(self):
        theme = ttk.Style(self.widget).theme_use()
        name = "Dark" if theme.endswith("dark") else "Light"
        return self.HIGH_ALERT[name]

    @property
    def destructive(self):
        """Use the theme's alert color for actions that discard user changes."""
        return self.high_alert.foreground


class ThemeMetrics:
    """Share the active theme's typography and scaled spacing within a form."""

    def __init__(self, widget):
        self.widget = widget
        self.colors = ThemeColors(widget)
        self.font = tkfont.Font(root=widget)
        self.heading_font = self.font.copy()
        self.refresh()

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

    def pixels(self, value):
        return round(value * self.scale)


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


def gesture_classification_color(theme_name, classification):
    """Return the active theme's semantic color for a finger classification."""
    palette = _GESTURE_COLORS.get(theme_name, _GESTURE_COLORS["Light"])
    key = getattr(classification, "value", classification)
    return palette.get(key, palette["straight"])


def gesture_bar_background(theme_name):
    """Return the theme's subdued track color for deviation bars."""
    return _GESTURE_BAR_BACKGROUNDS.get(
        theme_name, _GESTURE_BAR_BACKGROUNDS["Light"]
    )


@dataclass(frozen=True)
class DeviationPalette:
    """Colors shared by live bars, editable bands, handles, and legends."""

    theme_name: str
    surface: str
    track: str
    foreground: str

    def classification(self, category):
        return gesture_classification_color(self.theme_name, category)


class DeviationTheme:
    """Resolve canvas colors from the application theme and active ttk styles."""

    def __init__(self, widget):
        self.widget = widget

    def palette(self, theme_name):
        style = ttk.Style(self.widget)
        surface = style.lookup("TFrame", "background")
        if not surface:
            suffix = "dark" if style.theme_use().endswith("dark") else "light"
            try:
                surface = self.widget.tk.call(
                    "set", f"::ttk::theme::sv_{suffix}::colors(-bg)"
                )
            except tk.TclError:
                pass
            surface = surface or self.widget.winfo_toplevel().cget("background")
        foreground = (
            style.lookup("TLabel", "foreground")
            or _TEXT_COLORS.get(theme_name, _TEXT_COLORS["Light"])
        )
        return DeviationPalette(
            theme_name, surface, gesture_bar_background(theme_name), foreground,
        )


def apply_theme(root, name, scale=1.0):
    """Apply the named theme at the given scale. Safe to call at any time."""
    if sv_ttk is not None:
        sv_ttk.set_theme(_MODES.get(name, "light"))
    else:
        ttk.Style(root).theme_use("clam")

    # Tk scaling is pixels per point: 96/72 at 100%
    root.tk.call("tk", "scaling", scale * 96 / 72)

    for font_name in _SV_FONTS:
        try:
            tkfont.nametofont(font_name).configure(size=BASE_FONT_SIZE)
        except tk.TclError:
            pass  # that font name doesn't exist in this sv-ttk version

    padding = (
        int(BASE_BUTTON_PADDING[0] * scale),
        int(BASE_BUTTON_PADDING[1] * scale),
    )
    style = ttk.Style(root)
    try:
        combo_font = tkfont.nametofont("SunValleyBodyFont")
        style.configure("TCombobox", font=combo_font)
        root.option_add("*TCombobox*Listbox.font", str(combo_font))
    except tk.TclError:
        pass
    style.configure("TButton", padding=padding)
    style.configure("Accent.TButton", padding=padding)

