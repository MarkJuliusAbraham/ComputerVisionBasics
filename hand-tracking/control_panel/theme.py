import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

import sv_ttk

# Our setting values -> sv-ttk's names
_MODES = {"Light": "light", "Dark": "dark"}

# Semantic gesture colors are defined with the app theme so labels stay readable
# on both theme backgrounds. Widgets request these styles by classification.
_GESTURE_COLORS = {
    "Light": {
        "straight": "#1e7e34",
        "partial": "#8a6100",
        "curled": "#b54708",
        "closed": "#c5221f",
    },
    "Dark": {
        "straight": "#81c995",
        "partial": "#fdd663",
        "curled": "#ffb77c",
        "closed": "#f28b82",
    },
}
_GESTURE_BAR_BACKGROUNDS = {"Light": "#a0a0a0", "Dark": "#595959"}

BASE_FONT_SIZE = 9            # points at 100%
BASE_BUTTON_PADDING = (8, 3)  # pixels at 100%

_SV_FONTS = ("SunValleyBodyFont", "SunValleyCaptionFont", "SunValleyBodyStrongFont")

_system_scale = None


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
    return palette.get(classification, palette["straight"])


def gesture_bar_background(theme_name):
    """Return the theme's subdued track color for deviation bars."""
    return _GESTURE_BAR_BACKGROUNDS.get(
        theme_name, _GESTURE_BAR_BACKGROUNDS["Light"]
    )


def apply_theme(root, name, scale=1.0):
    """Apply the named theme at the given scale. Safe to call at any time."""
    sv_ttk.set_theme(_MODES.get(name, "light"))

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
    style.configure("TButton", padding=padding)
    style.configure("Accent.TButton", padding=padding)
