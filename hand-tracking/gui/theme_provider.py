"""Theme and font construction for the Dear PyGui control surface."""

import os
from pathlib import Path
from uuid import uuid4


PALETTES = {
    "Dark": dict(
        bg=(15, 17, 22), card=(24, 27, 34), popup=(28, 31, 40),
        frame=(36, 40, 51), frame_hover=(46, 51, 65), frame_active=(58, 64, 82),
        border=(44, 49, 62), text=(232, 234, 240), muted=(140, 150, 168),
        accent=(99, 102, 241), accent_hover=(129, 140, 248),
        soft=(46, 50, 102), soft_hover=(60, 65, 130), row_alt=(255, 255, 255, 8),
    ),
    "Light": dict(
        bg=(243, 244, 247), card=(255, 255, 255), popup=(255, 255, 255),
        frame=(232, 235, 241), frame_hover=(221, 225, 234), frame_active=(208, 214, 227),
        border=(222, 226, 234), text=(17, 24, 39), muted=(107, 114, 128),
        accent=(79, 70, 229), accent_hover=(99, 102, 241),
        soft=(224, 231, 255), soft_hover=(199, 210, 254), row_alt=(0, 0, 0, 8),
    ),
}

COLOR_MAP = {
    "mvThemeCol_Text": "text", "mvThemeCol_TextDisabled": "muted",
    "mvThemeCol_TextSelectedBg": "soft_hover", "mvThemeCol_WindowBg": "bg",
    "mvThemeCol_ChildBg": "card", "mvThemeCol_PopupBg": "popup",
    "mvThemeCol_Border": "border", "mvThemeCol_Separator": "border",
    "mvThemeCol_FrameBg": "frame", "mvThemeCol_FrameBgHovered": "frame_hover",
    "mvThemeCol_FrameBgActive": "frame_active", "mvThemeCol_TitleBg": "card",
    "mvThemeCol_TitleBgActive": "card", "mvThemeCol_TitleBgCollapsed": "card",
    "mvThemeCol_ScrollbarGrab": "frame_active", "mvThemeCol_ScrollbarGrabHovered": "muted",
    "mvThemeCol_ScrollbarGrabActive": "accent", "mvThemeCol_CheckMark": "accent",
    "mvThemeCol_SliderGrab": "accent", "mvThemeCol_SliderGrabActive": "accent_hover",
    "mvThemeCol_Button": "frame", "mvThemeCol_ButtonHovered": "frame_hover",
    "mvThemeCol_ButtonActive": "frame_active", "mvThemeCol_Header": "soft",
    "mvThemeCol_HeaderHovered": "soft_hover", "mvThemeCol_HeaderActive": "soft_hover",
    "mvThemeCol_Tab": "frame", "mvThemeCol_TabHovered": "soft_hover",
    "mvThemeCol_TabActive": "soft", "mvThemeCol_TabUnfocused": "frame",
    "mvThemeCol_TabUnfocusedActive": "soft", "mvThemeCol_TableHeaderBg": "frame",
    "mvThemeCol_TableBorderStrong": "border", "mvThemeCol_TableBorderLight": "border",
    "mvThemeCol_TableRowBgAlt": "row_alt", "mvThemeCol_PlotHistogram": "accent",
    "mvThemeCol_PlotHistogramHovered": "accent_hover",
}
TRANSPARENT_COLORS = ("mvThemeCol_ScrollbarBg", "mvThemeCol_TableRowBg")
STYLE_MAP = {
    "mvStyleVar_WindowPadding": (16, 14), "mvStyleVar_FramePadding": (10, 7),
    "mvStyleVar_ItemSpacing": (10, 10), "mvStyleVar_ItemInnerSpacing": (8, 6),
    "mvStyleVar_CellPadding": (8, 7), "mvStyleVar_ScrollbarSize": 12,
    "mvStyleVar_GrabMinSize": 14, "mvStyleVar_WindowRounding": 12,
    "mvStyleVar_ChildRounding": 12, "mvStyleVar_FrameRounding": 8,
    "mvStyleVar_PopupRounding": 10, "mvStyleVar_ScrollbarRounding": 12,
    "mvStyleVar_GrabRounding": 8, "mvStyleVar_TabRounding": 8,
    "mvStyleVar_WindowBorderSize": 1, "mvStyleVar_ChildBorderSize": 1,
    "mvStyleVar_PopupBorderSize": 1, "mvStyleVar_FrameBorderSize": 0,
}
BUTTON_STYLES = {
    "primary": ((99, 102, 241, 255), (129, 140, 248, 255), (79, 70, 229, 255)),
    "danger": ((220, 38, 38, 255), (239, 68, 68, 255), (185, 28, 28, 255)),
}
FONT_OVERSAMPLE = 2
BODY_FONT_PX = 17
HEADING_FONT_PX = 23
FONT_DIRS = (
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
    Path("/System/Library/Fonts/Supplemental"),
    Path("/usr/share/fonts/truetype/dejavu"),
)
BODY_FONTS = ("segoeui.ttf", "arial.ttf", "Arial.ttf", "DejaVuSans.ttf")
HEADING_FONTS = (
    "seguisb.ttf", "segoeuib.ttf", "arialbd.ttf", "Arial Bold.ttf",
    "DejaVuSans-Bold.ttf",
)


def _rgba(color):
    return tuple(color) if len(color) == 4 else (*color, 255)


def _find_font(names):
    for folder in FONT_DIRS:
        for name in names:
            path = folder / name
            if path.exists():
                return path
    return None


class ThemeProvider:
    """Create and replace application themes for a Dear PyGui context."""

    def __init__(self, dpg, scale):
        self.dpg = dpg
        self.scale = scale
        self.current_tag = None
        self.button_themes = {}
        self.name = None
        self.body_font = None
        self.heading_font = None
        self.oversample = 1

    def load_fonts(self):
        dpg = self.dpg
        body = _find_font(BODY_FONTS)
        heading = _find_font(HEADING_FONTS) or body
        if body is None:
            return
        try:
            with dpg.font_registry():
                self.body_font = self._add_font(body, BODY_FONT_PX)
                self.heading_font = self._add_font(heading, HEADING_FONT_PX)
            dpg.bind_font(self.body_font)
            self.oversample = FONT_OVERSAMPLE
        except Exception:
            self.body_font = self.heading_font = None
            self.oversample = 1

    def _add_font(self, path, size):
        with self.dpg.font(str(path), size * FONT_OVERSAMPLE) as font:
            self.dpg.add_font_chars([0x2014, 0x2026, 0x00B7, 0x00B0])
        return font

    def build_button_themes(self):
        dpg = self.dpg
        for key, (base, hover, active) in BUTTON_STYLES.items():
            with dpg.theme() as theme:
                with dpg.theme_component(dpg.mvButton):
                    dpg.add_theme_color(dpg.mvThemeCol_Button, base, category=dpg.mvThemeCat_Core)
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, hover, category=dpg.mvThemeCat_Core)
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, active, category=dpg.mvThemeCat_Core)
                    dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255), category=dpg.mvThemeCat_Core)
            self.button_themes[key] = theme

    def apply(self, name):
        dpg = self.dpg
        palette = PALETTES["Dark" if name == "Dark" else "Light"]
        tag = f"app_theme_{uuid4().hex[:8]}"
        with dpg.theme(tag=tag):
            with dpg.theme_component(dpg.mvAll):
                for color_name, key in COLOR_MAP.items():
                    constant = getattr(dpg, color_name, None)
                    if constant is not None:
                        dpg.add_theme_color(constant, _rgba(palette[key]), category=dpg.mvThemeCat_Core)
                for color_name in TRANSPARENT_COLORS:
                    constant = getattr(dpg, color_name, None)
                    if constant is not None:
                        dpg.add_theme_color(constant, (0, 0, 0, 0), category=dpg.mvThemeCat_Core)
                dim = getattr(dpg, "mvThemeCol_ModalWindowDimBg", None)
                if dim is not None:
                    dpg.add_theme_color(dim, (0, 0, 0, 120), category=dpg.mvThemeCat_Core)
                for style_name, value in STYLE_MAP.items():
                    constant = getattr(dpg, style_name, None)
                    if constant is None:
                        continue
                    values = value if isinstance(value, tuple) else (value,)
                    dpg.add_theme_style(constant, *(self.scale(v) for v in values),
                                        category=dpg.mvThemeCat_Core)
        dpg.bind_theme(tag)
        if self.current_tag and dpg.does_item_exist(self.current_tag):
            dpg.delete_item(self.current_tag)
        self.current_tag = tag
        self.name = name
