"""Dear PyGui control surface for the hand tracking application.

The camera and gesture pipeline call this class through a small event-loop API
(`after`, `run`, and the update methods below), keeping UI toolkit details out
of Application.
"""

from copy import deepcopy
from dataclasses import replace
import ctypes
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

from settings.settings_manager import (
    SettingsData, THEMES, UI_SCALES, default_finger_thresholds,
    resize_finger_thresholds,
)
from gestures.finger_classifier import finger_categories
from gestures.gesture_config import (
    CommandSequence, CommandStep, GestureConfig, GestureDefinition,
    GestureMatch, RepeatSettings,
)
from gestures.profile_manager import GestureProfileManager
from gui.scheduler import CallbackScheduler
from gui.mapping_model import MappingModel
from gui.panel_constants import FINGER_NAMES, MUTED, PALM_OPTIONS
from gui.panels import MainPanel, MappingPanel, SettingsPanel


# --- Look and feel -----------------------------------------------------------
# Change `accent` / `accent_hover` / `soft` / `soft_hover` to re-colour the UI.
PALETTES = {
    "Dark": dict(
        bg=(15, 17, 22), card=(24, 27, 34), popup=(28, 31, 40),
        frame=(36, 40, 51), frame_hover=(46, 51, 65), frame_active=(58, 64, 82),
        border=(44, 49, 62), text=(232, 234, 240), muted=(140, 150, 168),
        accent=(99, 102, 241), accent_hover=(129, 140, 248),
        soft=(46, 50, 102), soft_hover=(60, 65, 130),
        row_alt=(255, 255, 255, 8),
    ),
    "Light": dict(
        bg=(243, 244, 247), card=(255, 255, 255), popup=(255, 255, 255),
        frame=(232, 235, 241), frame_hover=(221, 225, 234), frame_active=(208, 214, 227),
        border=(222, 226, 234), text=(17, 24, 39), muted=(107, 114, 128),
        accent=(79, 70, 229), accent_hover=(99, 102, 241),
        soft=(224, 231, 255), soft_hover=(199, 210, 254),
        row_alt=(0, 0, 0, 8),
    ),
}
# Dear PyGui colour names -> palette keys (looked up by name so a missing
# constant in an older Dear PyGui build is skipped instead of crashing).
COLOR_MAP = {
    "mvThemeCol_Text": "text",
    "mvThemeCol_TextDisabled": "muted",
    "mvThemeCol_TextSelectedBg": "soft_hover",
    "mvThemeCol_WindowBg": "bg",
    "mvThemeCol_ChildBg": "card",
    "mvThemeCol_PopupBg": "popup",
    "mvThemeCol_Border": "border",
    "mvThemeCol_Separator": "border",
    "mvThemeCol_FrameBg": "frame",
    "mvThemeCol_FrameBgHovered": "frame_hover",
    "mvThemeCol_FrameBgActive": "frame_active",
    "mvThemeCol_TitleBg": "card",
    "mvThemeCol_TitleBgActive": "card",
    "mvThemeCol_TitleBgCollapsed": "card",
    "mvThemeCol_ScrollbarGrab": "frame_active",
    "mvThemeCol_ScrollbarGrabHovered": "muted",
    "mvThemeCol_ScrollbarGrabActive": "accent",
    "mvThemeCol_CheckMark": "accent",
    "mvThemeCol_SliderGrab": "accent",
    "mvThemeCol_SliderGrabActive": "accent_hover",
    "mvThemeCol_Button": "frame",
    "mvThemeCol_ButtonHovered": "frame_hover",
    "mvThemeCol_ButtonActive": "frame_active",
    "mvThemeCol_Header": "soft",
    "mvThemeCol_HeaderHovered": "soft_hover",
    "mvThemeCol_HeaderActive": "soft_hover",
    "mvThemeCol_Tab": "frame",
    "mvThemeCol_TabHovered": "soft_hover",
    "mvThemeCol_TabActive": "soft",
    "mvThemeCol_TabUnfocused": "frame",
    "mvThemeCol_TabUnfocusedActive": "soft",
    "mvThemeCol_TableHeaderBg": "frame",
    "mvThemeCol_TableBorderStrong": "border",
    "mvThemeCol_TableBorderLight": "border",
    "mvThemeCol_TableRowBgAlt": "row_alt",
    "mvThemeCol_PlotHistogram": "accent",          # progress bar fill
    "mvThemeCol_PlotHistogramHovered": "accent_hover",
}
TRANSPARENT_COLORS = ("mvThemeCol_ScrollbarBg", "mvThemeCol_TableRowBg")

# Style variables in logical pixels (tuples take x, y).
STYLE_MAP = {
    "mvStyleVar_WindowPadding": (16, 14),
    "mvStyleVar_FramePadding": (10, 7),
    "mvStyleVar_ItemSpacing": (10, 10),
    "mvStyleVar_ItemInnerSpacing": (8, 6),
    "mvStyleVar_CellPadding": (8, 7),
    "mvStyleVar_ScrollbarSize": 12,
    "mvStyleVar_GrabMinSize": 14,
    "mvStyleVar_WindowRounding": 12,
    "mvStyleVar_ChildRounding": 12,
    "mvStyleVar_FrameRounding": 8,
    "mvStyleVar_PopupRounding": 10,
    "mvStyleVar_ScrollbarRounding": 12,
    "mvStyleVar_GrabRounding": 8,
    "mvStyleVar_TabRounding": 8,
    "mvStyleVar_WindowBorderSize": 1,
    "mvStyleVar_ChildBorderSize": 1,
    "mvStyleVar_PopupBorderSize": 1,
    "mvStyleVar_FrameBorderSize": 0,
}

# Buttons that get their own colours: (normal, hovered, pressed), white text.
BUTTON_STYLES = {
    "primary": ((99, 102, 241, 255), (129, 140, 248, 255), (79, 70, 229, 255)),
    "danger": ((220, 38, 38, 255), (239, 68, 68, 255), (185, 28, 28, 255)),
}

# Fonts are loaded at FONT_OVERSAMPLE x their size and scaled back down, which
# keeps text crisp when the UI scale setting enlarges it.
FONT_OVERSAMPLE = 2
BODY_FONT_PX = 17
HEADING_FONT_PX = 23
FONT_DIRS = (
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
    Path("/System/Library/Fonts/Supplemental"),
    Path("/usr/share/fonts/truetype/dejavu"),
)
BODY_FONTS = ("segoeui.ttf", "arial.ttf", "Arial.ttf", "DejaVuSans.ttf")
HEADING_FONTS = ("seguisb.ttf", "segoeuib.ttf", "arialbd.ttf", "Arial Bold.ttf",
                 "DejaVuSans-Bold.ttf")


def _enable_dpi_awareness():
    """Ask Windows not to bitmap-stretch the window; return the display scale."""
    if sys.platform != "win32":
        return 1.0
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    try:
        return max(1.0, ctypes.windll.user32.GetDpiForSystem() / 96.0)
    except Exception:
        return 1.0


def _find_font(names):
    for folder in FONT_DIRS:
        for name in names:
            path = folder / name
            if path.exists():
                return path
    return None


def _rgba(color):
    return tuple(color) if len(color) == 4 else (*color, 255)


class ControlWindow:
    """Immediate-mode Dear PyGui controls, preserving the Application API."""

    UI_FRAME_INTERVAL = 1.0 / 60.0

    def __init__(
        self, on_restart, on_close, settings, on_settings_path=None,
        on_apply=None, camera_index=0, on_camera_switch=None,
        on_toggle_tracking=None, on_tracking_tab_active=None,
        on_mapping_saved=None,
    ):
        try:
            import dearpygui.dearpygui as dpg
        except ImportError as error:
            raise RuntimeError(
                "Dear PyGui is required for the control interface. "
                "Install it with `pip install -r requirements-ui.txt`."
            ) from error

        self.dpg = dpg
        self._main_panel = MainPanel(self)
        self._settings_panel = SettingsPanel(self)
        self._mapping_panel = MappingPanel(self)
        self._dpi = _enable_dpi_awareness()
        self._font_body = None
        self._font_heading = None
        self._font_oversample = 1
        self._theme_tag = None
        self._button_themes = {}
        self.on_restart = on_restart
        self.on_close = on_close
        self._pending_close_action = on_close
        self.on_settings_path = on_settings_path
        self.on_apply = on_apply
        self.on_camera_switch = on_camera_switch
        self.on_toggle_tracking = on_toggle_tracking
        self.on_tracking_tab_active = on_tracking_tab_active
        self.on_mapping_saved = on_mapping_saved
        self.settings = settings
        self._settings_draft = deepcopy(settings.data)
        self.baseline = deepcopy(settings.data)
        self.paused = False
        self._latest_hand_states = []
        self._preview_fingers = None
        self._preview_status = "No hand detected"
        self._camera_index = camera_index
        self._camera_active = False
        self._camera_switching = True
        self._scheduler = CallbackScheduler()
        self._running = True
        self._close_pending = False
        self._close_finalized = False
        self._active_tab = "Main"
        self._mapping_status = "Gesture mappings loaded"
        self._settings_status = ""
        self._settings_dirty = False
        self._mapping_dirty = False
        self._profile_manager = GestureProfileManager()
        self._profile_browse_folder = str(
            self._profile_manager._folder_for(self._profile_manager.source_path)
        )
        self._load_mapping_state()

        dpg.create_context()
        self._closed = False
        try:
            dpg.configure_app(manual_callback_management=True)
            self._load_fonts()
            self._build_item_themes()
            dpg.create_viewport(title="Hand Tracking Controls",
                                width=self._px(1020), height=self._px(800),
                                min_width=self._px(820), min_height=self._px(620),
                                resizable=True, disable_close=True, vsync=False)
            dpg.set_exit_callback(self._request_close)
            self._build_theme(settings.data.theme)
            self._build_ui(settings.data)
            dpg.setup_dearpygui()
            dpg.show_viewport()
            dpg.set_primary_window("control_root", True)
            self._apply_scale(settings.data.ui_scale)
        except BaseException:
            dpg.destroy_context()
            self._closed = True
            raise

    # Look and feel helpers
    def _px(self, value):
        return int(round(value * self._dpi))

    def _load_fonts(self):
        dpg = self.dpg
        body = _find_font(BODY_FONTS)
        heading = _find_font(HEADING_FONTS) or body
        if body is None:
            return  # fall back to Dear PyGui's built-in font
        try:
            with dpg.font_registry():
                self._font_body = self._add_font(body, BODY_FONT_PX)
                self._font_heading = self._add_font(heading, HEADING_FONT_PX)
            dpg.bind_font(self._font_body)
            self._font_oversample = FONT_OVERSAMPLE
        except Exception:
            self._font_body = self._font_heading = None
            self._font_oversample = 1

    def _add_font(self, path, size):
        dpg = self.dpg
        with dpg.font(str(path), size * FONT_OVERSAMPLE) as font:
            dpg.add_font_chars([0x2014, 0x2026, 0x00B7, 0x00B0])
        return font

    def _build_item_themes(self):
        dpg = self.dpg
        for key, (base, hover, active) in BUTTON_STYLES.items():
            with dpg.theme() as theme:
                with dpg.theme_component(dpg.mvButton):
                    dpg.add_theme_color(dpg.mvThemeCol_Button, base, category=dpg.mvThemeCat_Core)
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, hover, category=dpg.mvThemeCat_Core)
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, active, category=dpg.mvThemeCat_Core)
                    dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255), category=dpg.mvThemeCat_Core)
            self._button_themes[key] = theme

    def _build_theme(self, name):
        dpg = self.dpg
        palette = PALETTES["Dark" if name == "Dark" else "Light"]
        previous = self._theme_tag
        tag = f"app_theme_{uuid4().hex[:8]}"
        with dpg.theme(tag=tag):
            with dpg.theme_component(dpg.mvAll):
                for color_name, key in COLOR_MAP.items():
                    constant = getattr(dpg, color_name, None)
                    if constant is not None:
                        dpg.add_theme_color(constant, _rgba(palette[key]),
                                            category=dpg.mvThemeCat_Core)
                for color_name in TRANSPARENT_COLORS:
                    constant = getattr(dpg, color_name, None)
                    if constant is not None:
                        dpg.add_theme_color(constant, (0, 0, 0, 0),
                                            category=dpg.mvThemeCat_Core)
                dim = getattr(dpg, "mvThemeCol_ModalWindowDimBg", None)
                if dim is not None:
                    dpg.add_theme_color(dim, (0, 0, 0, 120), category=dpg.mvThemeCat_Core)
                for style_name, value in STYLE_MAP.items():
                    constant = getattr(dpg, style_name, None)
                    if constant is None:
                        continue
                    values = value if isinstance(value, tuple) else (value,)
                    dpg.add_theme_style(constant, *(self._px(v) for v in values),
                                        category=dpg.mvThemeCat_Core)
        dpg.bind_theme(tag)
        if previous and dpg.does_item_exist(previous):
            dpg.delete_item(previous)
        self._theme_tag = tag
        self.theme_name = name

    def _heading(self, text, **kwargs):
        item = self.dpg.add_text(text, **kwargs)
        if self._font_heading:
            self.dpg.bind_item_font(item, self._font_heading)
        return item

    def _caption(self, text, **kwargs):
        return self.dpg.add_text(text.upper(), color=MUTED, **kwargs)

    def _button(self, label, callback, style=None, **kwargs):
        item = self.dpg.add_button(label=label, callback=callback, **kwargs)
        if style:
            self.dpg.bind_item_theme(item, self._button_themes[style])
        return item

    def _spacer(self, height=6):
        self.dpg.add_spacer(height=self._px(height))

    def _build_ui(self, data):
        dpg = self.dpg
        self._main_ids = {}
        self._setting_ids = {}
        with dpg.window(tag="control_root", label="Hand Tracking Controls", no_close=True):
            with dpg.tab_bar(tag="root_tabs", callback=self._tab_changed):
                with dpg.tab(label="  Main  ", tag="tab_main"):
                    self._spacer(4)
                    self._build_main(data)
                with dpg.tab(label="  Settings  ", tag="tab_settings"):
                    self._spacer(4)
                    self._build_settings(data)
                with dpg.tab(label="  Mapping  ", tag="tab_mapping"):
                    self._spacer(4)
                    self._build_mapping()

        with dpg.file_dialog(tag="settings_dialog", show=False, modal=True,
                             directory_selector=False,
                             width=self._px(720), height=self._px(440),
                             callback=self._settings_file_selected):
            dpg.add_file_extension(".json", color=(120, 200, 120, 255))
            dpg.add_file_extension(".*")
        with dpg.file_dialog(tag="profile_folder_dialog", show=False, modal=True,
                             directory_selector=True,
                             width=self._px(720), height=self._px(440),
                             callback=self._profile_folder_selected):
            pass
        with dpg.file_dialog(tag="profile_file_dialog", show=False, modal=True,
                             directory_selector=False,
                             width=self._px(720), height=self._px(440),
                             callback=self._profile_file_selected):
            dpg.add_file_extension(".json", color=(120, 200, 120, 255))

    def _build_main(self, data):
        return self._main_panel.build()

    def _legacy_build_main(self, data):
        dpg = self.dpg
        self._heading("Live tracking")
        with dpg.group(horizontal=True):
            self._main_ids["pause"] = self._button(
                "Pause tracking", self._toggle_tracking, style="primary"
            )
            self._button("Restart", self._request_restart)
            self._button("Exit", self._request_close, style="danger")
        self._spacer(4)
        with dpg.child_window(auto_resize_y=True, border=True, no_scrollbar=True, no_scroll_with_mouse=True):
            self._caption("Camera device")
            with dpg.group(horizontal=True):
                self._main_ids["camera_picker"] = dpg.add_combo(
                    [str(i) for i in range(10)], default_value=str(self._camera_index),
                    width=self._px(90), tag="camera_picker",
                )
                self._main_ids["camera_switch"] = self._button(
                    "Switch camera", self._switch_camera
                )
            self._main_ids["camera_status"] = dpg.add_text("Opening camera…")
        self._spacer(4)
        self._caption("Live gesture data")
        self._main_ids["tracking_status"] = dpg.add_text("Waiting for camera…")
        with dpg.table(header_row=False, policy=dpg.mvTable_SizingStretchSame):
            dpg.add_table_column()
            dpg.add_table_column()
            with dpg.table_row():
                for handedness in ("Left", "Right"):
                    with dpg.child_window(width=-1, auto_resize_y=True, border=True, no_scrollbar=True, no_scroll_with_mouse=True):
                        self._heading(f"{handedness} hand")
                        palm = dpg.add_text("Palm: —")
                        command = dpg.add_text("Command: —")
                        dpg.add_separator()
                        fingers = {}
                        # dpg.add_text() has no `width` argument, so a table gives
                        # the name / bar / score columns their widths instead.
                        with dpg.table(header_row=False):
                            dpg.add_table_column(width_fixed=True,
                                                 init_width_or_weight=self._px(80))
                            dpg.add_table_column(width_stretch=True,
                                                 init_width_or_weight=1.0)
                            dpg.add_table_column(width_fixed=True,
                                                 init_width_or_weight=self._px(84))
                            for name in FINGER_NAMES:
                                with dpg.table_row():
                                    dpg.add_text(name.title())
                                    bar = dpg.add_progress_bar(
                                        default_value=0, width=-1,
                                        height=self._px(22), overlay="—",
                                    )
                                    score = dpg.add_text("—")
                                    fingers[name] = (bar, score)
                    self._main_ids[handedness] = {
                        "palm": palm, "command": command, "fingers": fingers,
                    }
        self._main_ids["hand_panel_group"] = None

    def _build_settings(self, data):
        return self._settings_panel.build(data)

    def _legacy_build_settings(self, data):
        dpg = self.dpg
        with dpg.group(horizontal=True):
            self._button("Apply changes", self._apply_settings, style="primary")
            self._setting_ids["status"] = dpg.add_text("")
        with dpg.group(horizontal=True):
            with dpg.child_window(width=self._px(200), height=-1, border=True, no_scrollbar=True, no_scroll_with_mouse=True):
                self._caption("Settings")
                self._setting_ids["topic"] = "Tracking"
                self._setting_ids["nav"] = {}
                for topic in ("Tracking", "Appearance", "Advanced"):
                    self._setting_ids["nav"][topic] = dpg.add_selectable(label=topic, default_value=topic == "Tracking",
                                       callback=self._select_settings_topic,
                                       user_data=topic, span_columns=True)
            with dpg.child_window(width=-1, height=-1, border=True):
                self._setting_ids["content"] = dpg.add_group()
        self._render_settings_topic(data, "Tracking")

    def _render_settings_topic(self, data, topic):
        dpg = self.dpg
        group = self._setting_ids["content"]
        dpg.delete_item(group, children_only=True)
        self._setting_ids["topic"] = topic
        for name, item in self._setting_ids.get("nav", {}).items():
            dpg.set_value(item, name == topic)
        with dpg.group(parent=group):
            self._heading(topic)
            dpg.add_separator()
            if topic == "Tracking":
                self._setting_ids["track_hands"] = dpg.add_checkbox(
                    label="Track hands", default_value=data.track_hands,
                    callback=self._settings_changed,
                )
                self._setting_ids["profile"] = dpg.add_checkbox(
                    label="Print FPS and detection latency", default_value=data.profile,
                    callback=self._settings_changed,
                )
                self._setting_ids["segment_count"] = dpg.add_combo(
                    ["4", "5", "6"], label="Deviation segments",
                    default_value=str(data.finger_segment_count), width=self._px(180),
                    callback=self._segment_count_changed,
                )
                self._setting_ids["calculation"] = dpg.add_combo(
                    ["default", "prototype"], label="Deviation calculation",
                    default_value=data.finger_deviation_calculation, width=self._px(180),
                    callback=self._settings_changed,
                )
                self._spacer(4)
                self._caption("Finger deviation ranges")
                self._setting_ids["thresholds"] = []
                for index, threshold in enumerate(data.finger_classification_thresholds):
                    tag = f"threshold_{index}"
                    self._setting_ids["thresholds"].append(tag)
                    dpg.add_slider_float(tag=tag, label=f"Split {index + 1}",
                                         min_value=0, max_value=120,
                                         default_value=threshold, width=-self._px(90),
                                         callback=self._settings_changed)
                self._spacer(4)
                self._setting_ids["test"] = self._button(
                    "Test deviation", self._toggle_preview
                )
                self._setting_ids["preview"] = dpg.add_text("No hand detected")
                self._setting_ids["preview_bars"] = dpg.add_group()
            elif topic == "Appearance":
                self._setting_ids["theme"] = dpg.add_combo(
                    list(THEMES), label="Theme", default_value=data.theme,
                    callback=self._theme_changed, width=self._px(180),
                )
                self._setting_ids["scale"] = dpg.add_combo(
                    list(UI_SCALES), label="UI scale", default_value=data.ui_scale,
                    callback=self._settings_changed, width=self._px(180),
                )
            else:
                self._caption("Settings file")
                with dpg.group(horizontal=True):
                    self._setting_ids["path"] = dpg.add_input_text(
                        default_value=self.settings.path, readonly=True,
                        width=-self._px(120),
                    )
                    self._button("Browse…", lambda: dpg.show_item("settings_dialog"))
                self._setting_ids["advanced_status"] = dpg.add_text("")
        self._refresh_settings_state()

    def _build_mapping(self):
        return self._mapping_panel.build()

    def _legacy_build_mapping(self):
        dpg = self.dpg
        self._mapping_tags = {}
        with dpg.child_window(width=-1, auto_resize_y=True, border=True, no_scrollbar=True, no_scroll_with_mouse=True):
            self._caption("Active gesture profile")
            self._mapping_tags["active_profile"] = self._heading(self._profile_display())
            with dpg.group(horizontal=True):
                self._button("More profiles", self._show_profile_window)
                self._mapping_tags["save"] = self._button(
                    "Save mappings", self._save_mapping, style="primary"
                )
                self._mapping_tags["status"] = dpg.add_text(self._mapping_status)
        self._spacer(2)
        with dpg.tab_bar():
            with dpg.tab(label="  Gesture  "):
                self._spacer(4)
                self._heading("Gesture")
                with dpg.group(horizontal=True):
                    self._mapping_tags["gesture_selector"] = dpg.add_combo(
                        [], width=self._px(260), callback=self._gesture_selected
                    )
                    self._button("Manage gestures", self._show_manage_window)
                dpg.add_separator()
                self._mapping_tags["palm"] = dpg.add_combo(
                    list(PALM_OPTIONS), label="Palm orientation", width=self._px(230),
                    callback=self._mapping_changed,
                )
                self._mapping_tags["tracked_finger"] = dpg.add_combo(
                    ["None", *(name.title() for name in FINGER_NAMES)],
                    label="Tracked fingertip", width=self._px(230),
                    callback=self._mapping_changed,
                )
                self._spacer(4)
                self._caption("Allowed finger positions (leave all unchecked for Any)")
                self._mapping_tags["finger_checks"] = {}
                self._render_finger_checks(parent=dpg.last_container())
            with dpg.tab(label="  Commands  "):
                self._spacer(4)
                self._heading("Command sequence")
                self._mapping_tags["commands"] = dpg.add_input_text(
                    label="Keys, one character per step separated by commas",
                    width=-self._px(340), callback=self._mapping_changed,
                )
                self._mapping_tags["delay"] = dpg.add_input_int(
                    label="Delay between steps (ms)", min_value=0, min_clamped=True,
                    width=self._px(220), callback=self._mapping_changed,
                )
            with dpg.tab(label="  Reset  "):
                self._spacer(4)
                self._heading("Reset gesture")
                self._mapping_tags["reset_palm"] = dpg.add_combo(
                    list(PALM_OPTIONS), label="Palm orientation", width=self._px(230),
                    callback=self._mapping_changed,
                )
                self._spacer(4)
                self._caption("Require each finger to match one of the checked positions")
                self._mapping_tags["reset_checks"] = {}
                self._render_reset_checks(parent=dpg.last_container())
            with dpg.tab(label="  Repeat  "):
                self._spacer(4)
                self._heading("Repeat behavior")
                dpg.add_text("Initial displacement is the dead zone before path distance begins accumulating.",
                             color=MUTED, wrap=0)
                self._spacer(4)
                for label, key, default, minimum, maximum, step in (
                    ("Initial displacement", "initial_displacement", 0.03, 0, .5, .01),
                    ("Path distance between repeats", "distance_threshold", .09, .01, 1, .01),
                    ("Minimum repeat interval (ms)", "min_interval_ms", 50, 0, 2000, 10),
                    ("Maximum repeats per gesture", "max_repeats", 2, 0, 20, 1),
                ):
                    create_input = dpg.add_input_int if key == "max_repeats" else dpg.add_input_float
                    self._mapping_tags[key] = create_input(
                        label=label, default_value=default, min_value=minimum,
                        max_value=maximum, width=self._px(270), step=step,
                        callback=self._mapping_changed,
                    )
        self._refresh_mapping_widgets()

        with dpg.window(label="Gesture Profiles", tag="profile_window", show=False,
                        modal=True, width=self._px(620), height=self._px(550)):
            dpg.add_text("Choose a folder or a profile file")
            with dpg.group(horizontal=True):
                dpg.add_input_text(tag="profile_location", default_value=self._profile_manager.source_path,
                                   readonly=True, width=-self._px(250))
                self._button("Browse folder", lambda: dpg.show_item("profile_folder_dialog"))
                self._button("Choose file", lambda: dpg.show_item("profile_file_dialog"))
            self._caption("Available profiles")
            dpg.add_listbox([], tag="profile_list", num_items=8, width=-1, callback=self._profile_selected)
            self._caption("Active profile")
            dpg.add_text(self._profile_display(), tag="profile_active_name")
            dpg.add_text("", tag="profile_status", wrap=0)
            with dpg.group(horizontal=True):
                dpg.add_input_text(tag="new_profile_name", hint="New profile name",
                                   width=-self._px(150))
                self._button("Create profile", self._create_profile, style="primary")
            self._button("Close", lambda: dpg.hide_item("profile_window"))

        with dpg.window(label="Manage Gestures", tag="manage_window", show=False,
                        modal=True, width=self._px(560), height=self._px(520),
                        on_close=self._close_manage_window):
            dpg.add_text("Gesture names are saved separately from mapping edits.",
                         color=MUTED)
            dpg.add_listbox([], tag="manage_list", num_items=10, width=-1,
                            callback=self._managed_selected)
            dpg.add_input_text(tag="manage_name", label="Name", width=-self._px(60),
                               callback=self._managed_name_changed)
            dpg.add_text("", tag="manage_status", wrap=0)
            with dpg.group(horizontal=True):
                self._button("Create", self._manage_create)
                self._button("Delete", self._manage_delete, style="danger")
                self._button("Save names", self._manage_save_names, style="primary")
                self._button("Close", self._close_manage_window)

    def _render_finger_checks(self, parent):
        dpg = self.dpg
        # Dynamic positional checkbox matrix follows the active 4–6 segment classifier.
        with dpg.table(header_row=True, parent=parent, tag="finger_table",
                       borders_innerH=True, borders_outerH=True,
                       borders_innerV=True, borders_outerV=True):
            dpg.add_table_column(label="Finger")
            for category in finger_categories(self.settings.data.finger_segment_count):
                dpg.add_table_column(label=category.label)
            for finger in FINGER_NAMES:
                with dpg.table_row():
                    dpg.add_text(finger.title())
                    self._mapping_tags["finger_checks"][finger] = {}
                    for category in finger_categories(self.settings.data.finger_segment_count):
                        tag = f"map_{finger}_{category.value}"
                        self._mapping_tags["finger_checks"][finger][category.value] = dpg.add_checkbox(
                            tag=tag, callback=self._mapping_changed
                        )

    def _render_reset_checks(self, parent):
        dpg = self.dpg
        with dpg.table(header_row=True, parent=parent, tag="reset_table",
                       borders_innerH=True, borders_outerH=True):
            dpg.add_table_column(label="Finger")
            for category in finger_categories(self.settings.data.finger_segment_count):
                dpg.add_table_column(label=category.label)
            for finger in FINGER_NAMES:
                with dpg.table_row():
                    dpg.add_text(finger.title())
                    self._mapping_tags["reset_checks"][finger] = {}
                    for category in finger_categories(self.settings.data.finger_segment_count):
                        tag = f"reset_{finger}_{category.value}"
                        self._mapping_tags["reset_checks"][finger][category.value] = dpg.add_checkbox(
                            tag=tag, callback=self._mapping_changed
                        )

    # Main tab updates
    def update_camera_state(self, state, requested, active, message=None):
        dpg = self.dpg
        if state in ("opening", "switching"):
            self._camera_switching = True
            text = f"Opening camera {requested}…"
            dpg.configure_item(self._main_ids["camera_switch"], enabled=False)
        elif state == "ready":
            self._camera_switching = False
            self._camera_active = True
            self._camera_index = active
            text = message or f"Using camera {active}"
            dpg.set_value("camera_picker", str(active))
            dpg.configure_item(self._main_ids["camera_switch"], enabled=True)
        else:
            self._camera_switching = False
            self._camera_active = False
            text = message or f"Could not open camera {requested}"
            dpg.configure_item(self._main_ids["camera_switch"], enabled=True)
        dpg.set_value(self._main_ids["camera_status"], text)

    def update_gesture_display(self, hand_states, enabled=True, paused=False):
        dpg = self.dpg
        self._latest_hand_states = hand_states
        record = hand_states[0] if hand_states else None
        self._preview_fingers = record["state"].fingers if record else None
        self._preview_status = (
            "Tracking disabled" if not enabled else "Tracking paused" if paused
            else "No hand detected" if record is None
            else f"Live data · {record['handedness']} hand"
        )
        status = ("Tracking disabled" if not enabled else "Tracking paused" if paused
                  else "No hands detected" if not hand_states else "Tracking active")
        dpg.set_value(self._main_ids["tracking_status"], status)
        for hand in ("Left", "Right"):
            ui = self._main_ids[hand]
            item = next((entry for entry in hand_states if entry["handedness"] == hand), None)
            dpg.set_value(ui["palm"], f"Palm: {item['state'].palm.value.replace('_', ' ').title()}" if item else "Palm: —")
            dpg.set_value(ui["command"], f"Command: {item['command'] or '—'}" if item else "Command: —")
            for finger, (bar, score) in ui["fingers"].items():
                finger_state = item["state"].fingers.get(finger) if item else None
                if finger_state is None:
                    dpg.set_value(bar, 0)
                    dpg.configure_item(bar, overlay="—")
                    dpg.set_value(score, "—")
                else:
                    value = max(0.0, min(1.0, finger_state.deviation / 120.0))
                    dpg.set_value(bar, value)
                    label = finger_state.position.label
                    dpg.configure_item(bar, overlay=label)
                    dpg.set_value(score, f"{finger_state.deviation:.1f}°")
        if self._setting_ids.get("topic") == "Tracking":
            self._render_preview()

    def set_tracking_paused(self, paused):
        self.paused = paused
        self.dpg.configure_item(self._main_ids["pause"],
                                label="Resume tracking" if paused else "Pause tracking")

    def _switch_camera(self):
        if self._camera_switching or not self.on_camera_switch:
            return
        try:
            index = int(self.dpg.get_value("camera_picker"))
        except (TypeError, ValueError):
            return
        self._camera_switching = True
        self.dpg.configure_item(self._main_ids["camera_switch"], enabled=False)
        self.dpg.set_value(self._main_ids["camera_status"], f"Opening camera {index}…")
        self.on_camera_switch(index)

    def _toggle_tracking(self):
        if self.on_toggle_tracking:
            self.on_toggle_tracking()

    # Settings draft/apply
    def _settings_values(self):
        dpg = self.dpg
        values = deepcopy(self._settings_draft)
        topic = self._setting_ids.get("topic")
        if topic == "Tracking" and "track_hands" in self._setting_ids:
            values.track_hands = dpg.get_value(self._setting_ids["track_hands"])
            values.profile = dpg.get_value(self._setting_ids["profile"])
            values.finger_segment_count = int(dpg.get_value(self._setting_ids["segment_count"]))
            values.finger_classification_thresholds = [dpg.get_value(tag) for tag in self._setting_ids["thresholds"]]
            values.finger_deviation_calculation = dpg.get_value(self._setting_ids["calculation"])
        elif topic == "Appearance":
            values.theme = dpg.get_value(self._setting_ids["theme"])
            values.ui_scale = dpg.get_value(self._setting_ids["scale"])
        self._settings_draft = deepcopy(values)
        return values

    def _settings_changed(self, *_):
        self._settings_draft = self._settings_values()
        self._settings_dirty = self._settings_draft != self.baseline
        self._refresh_settings_state()
        self._render_preview()

    def _segment_count_changed(self, *_):
        try:
            value = int(self.dpg.get_value(self._setting_ids["segment_count"]))
            thresholds = resize_finger_thresholds(self._settings_values().finger_classification_thresholds, value)
        except (ValueError, TypeError):
            thresholds = default_finger_thresholds(4)
            value = 4
        self._render_settings_topic(replace(self._settings_values(), finger_segment_count=value,
                                            finger_classification_thresholds=thresholds), "Tracking")
        self._settings_changed()

    def _theme_changed(self, *_):
        self._settings_changed()

    def _refresh_settings_state(self):
        if "status" in self._setting_ids and self.dpg.does_item_exist(self._setting_ids["status"]):
            self.dpg.set_value(self._setting_ids["status"], "Unsaved settings changes" if self._settings_dirty else self._settings_status)

    def _apply_settings(self):
        try:
            values = self._settings_values()
            if not values.has_valid_finger_thresholds():
                raise ValueError("Deviation splits must be in increasing order.")
            if self.on_apply:
                self.on_apply(values)
            else:
                self.settings.update(values)
            self.baseline = deepcopy(values)
            self._settings_draft = deepcopy(values)
            self._settings_dirty = False
            self._settings_status = "Settings saved"
            self._refresh_settings_state()
            self._apply_scale(values.ui_scale)
            if values.theme != self.theme_name:
                self._build_theme(values.theme)
            self._render_settings_topic(values, self._setting_ids["topic"])
            if hasattr(self, "_mapping_tags"):
                self._set_segment_count(values.finger_segment_count)
            return True
        except (ValueError, OSError) as error:
            self._settings_status = str(error)
            self.dpg.set_value(self._setting_ids["status"], self._settings_status)
            return False

    def _apply_scale(self, scale):
        factor = {"Auto": 1.0, "100%": 1.0, "125%": 1.25, "150%": 1.5,
                  "175%": 1.75, "200%": 2.0}.get(scale, 1.0)
        # Fonts are loaded oversampled, so divide that back out here.
        self.dpg.set_global_font_scale(factor * self._dpi / self._font_oversample)

    def _select_settings_topic(self, _sender, _app_data, topic):
        data = self._settings_values()
        self._render_settings_topic(data, topic)

    def _toggle_preview(self):
        self._setting_ids["preview_enabled"] = not self._setting_ids.get("preview_enabled", False)
        self.dpg.configure_item(self._setting_ids["test"], label="Stop preview" if self._setting_ids["preview_enabled"] else "Test deviation")
        self._render_preview()

    @property
    def tracking_preview_active(self):
        return (self._active_tab == "Settings"
                and self._setting_ids.get("topic") == "Tracking"
                and self._setting_ids.get("preview_enabled", False))

    def _render_preview(self):
        if "preview" not in self._setting_ids or not self.dpg.does_item_exist(self._setting_ids["preview"]):
            return
        self.dpg.set_value(self._setting_ids["preview"], self._preview_status)
        group = self._setting_ids.get("preview_bars")
        if not group or not self.dpg.does_item_exist(group):
            return
        enabled = self._setting_ids.get("preview_enabled", False)
        self.dpg.configure_item(group, show=enabled)
        bars = self._setting_ids.get("preview_items", {})
        if not bars or not all(self.dpg.does_item_exist(item) for item in bars.values()):
            bars = {name: self.dpg.add_progress_bar(default_value=0, overlay="—",
                                                   label=name.title(), width=-self._px(100),
                                                   parent=group)
                    for name in FINGER_NAMES}
            self._setting_ids["preview_items"] = bars
        values = self._settings_draft
        for name, bar in bars.items():
            state = (self._preview_fingers or {}).get(name)
            value = max(0, min(1, state.deviation / 120)) if state else 0
            label = "—"
            if state:
                category = values.classify_finger_deviation(state.deviation)
                label = f"{category.label} · {state.deviation:.1f}°"
            self.dpg.set_value(bar, value)
            self.dpg.configure_item(bar, overlay=label)

    def show_settings(self, settings):
        self.settings = settings
        self.baseline = deepcopy(settings.data)
        self._settings_draft = deepcopy(settings.data)
        self._settings_dirty = False
        self._render_settings_topic(settings.data, self._setting_ids["topic"])
        self._apply_scale(settings.data.ui_scale)
        self._build_theme(settings.data.theme)
        self._set_segment_count(settings.data.finger_segment_count)

    # Settings picker / outer event loop
    def _settings_file_selected(self, _sender, app_data):
        path = app_data.get("file_path_name") if isinstance(app_data, dict) else None
        if path and self.on_settings_path:
            try:
                self.on_settings_path(path)
                if self.dpg.does_item_exist(self._setting_ids.get("path", "")):
                    self.dpg.set_value(self._setting_ids["path"], path)
            except (ValueError, OSError) as error:
                self._settings_status = str(error)

    def after(self, delay_ms, callback):
        self._scheduler.schedule(delay_ms, callback)

    def run(self):
        dpg = self.dpg
        next_render = time.monotonic()
        while self._running and dpg.is_dearpygui_running():
            dpg.run_callbacks(dpg.get_callback_queue())
            if not self._running or not dpg.is_dearpygui_running():
                break
            now = time.monotonic()
            for _deadline, callback in self._scheduler.pop_due(now):
                if not self._running:
                    break
                callback()
            if self._close_pending:
                self._close_pending = False
                if self._settings_dirty or self._mapping_dirty:
                    self._show_unsaved_dialog()
                else:
                    self._finish_close()
            if self._running and dpg.is_dearpygui_running():
                now = time.monotonic()
                if now >= next_render:
                    dpg.render_dearpygui_frame()
                    next_render = time.monotonic() + self.UI_FRAME_INTERVAL
                else:
                    # Keep camera/command callbacks independent of UI refresh.
                    next_callback = self._scheduler.next_deadline(next_render)
                    time.sleep(max(0.0, min(next_render, next_callback) - now))

    def quit(self):
        self._running = False
        self.dpg.stop_dearpygui()

    def close(self):
        if self._closed:
            return
        self._running = False
        self._close_pending = False
        try:
            if self.dpg.is_dearpygui_running():
                self.dpg.stop_dearpygui()
            # Retire the native viewport before destroying the context.  This
            # matters when main.py immediately constructs the next application
            # during a restart; otherwise the previous OS window can linger.
            try:
                self.dpg.configure_viewport(0, show=False)
            except Exception:
                pass
        finally:
            self.dpg.destroy_context()
            self._closed = True

    def _request_close(self, *_):
        if self._closed or self._close_finalized or self._close_pending:
            return
        self._pending_close_action = self.on_close
        self._close_pending = True

    def _request_restart(self):
        if self._closed or self._close_finalized or self._close_pending:
            return
        self._pending_close_action = self.on_restart
        self._close_pending = True

    def _finish_close(self):
        if self._close_finalized:
            return
        self._close_finalized = True
        action = self._pending_close_action
        is_restart = action == self.on_restart
        if action:
            action()
        if is_restart:
            # Restart is handled in place by Application. Keep this viewport
            # and event loop alive, and allow a later real close request.
            self._close_finalized = False
            self._close_pending = False
            self._pending_close_action = self.on_close
            return
        if self._running:
            self.quit()

    def _show_unsaved_dialog(self):
        dpg = self.dpg
        if dpg.does_item_exist("unsaved_dialog"):
            dpg.delete_item("unsaved_dialog")
        with dpg.window(label="Unsaved changes", tag="unsaved_dialog", modal=True,
                        autosize=True, pos=(self._px(280), self._px(250))):
            dpg.add_text("There are unsaved changes.")
            self._spacer(6)
            with dpg.group(horizontal=True):
                self._button("Save", self._save_and_close, style="primary")
                self._button("Discard", self._discard_and_close, style="danger")
                self._button("Cancel", lambda: dpg.delete_item("unsaved_dialog"))

    def _save_and_close(self):
        if self._settings_dirty:
            self._apply_settings()
            if self._settings_dirty:
                return
        if self._mapping_dirty and not self._save_mapping():
            return
        self._finish_close()

    def _discard_and_close(self):
        if self._settings_dirty:
            self._discard_settings()
        if self._mapping_dirty:
            self._load_mapping_state()
            self._refresh_mapping_widgets()
        self._finish_close()

    def _tab_changed(self, _sender, app_data):
        label = self.dpg.get_item_label(app_data).strip()
        if self._active_tab == "Mapping" and label != "Mapping" and self._mapping_dirty:
            self.dpg.set_value("root_tabs", self.dpg.get_alias_id("tab_mapping"))
            self._show_mapping_leave_dialog(label)
            return
        if self._active_tab == "Settings" and label != "Settings" and self._settings_dirty:
            self.dpg.set_value("root_tabs", self.dpg.get_alias_id("tab_settings"))
            self._show_settings_leave_dialog(label)
            return
        self._active_tab = label
        if self.on_tracking_tab_active:
            self.on_tracking_tab_active(label == "Main")

    def _show_mapping_leave_dialog(self, target):
        self._show_leave_dialog("Mapping changes", "mapping_leave", target,
                                self._save_mapping, self._discard_mapping)

    def _show_settings_leave_dialog(self, target):
        self._show_leave_dialog("Settings changes", "settings_leave", target,
                                self._apply_settings, self._discard_settings)

    def _show_leave_dialog(self, title, tag, target, save, discard):
        dpg = self.dpg
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)
        with dpg.window(label=title, tag=tag, modal=True,
                        autosize=True):
            dpg.add_text("Save your changes before leaving?")
            self._spacer(6)
            with dpg.group(horizontal=True):
                self._button("Save", lambda: self._leave_after(save, tag, target), style="primary")
                self._button("Discard", lambda: self._leave_after(discard, tag, target), style="danger")
                self._button("Cancel", lambda: dpg.delete_item(tag))

    def _leave_after(self, action, dialog, target):
        result = action()
        if result is False:
            return
        self.dpg.delete_item(dialog)
        self._active_tab = target
        tab = "tab_main" if target == "Main" else "tab_settings" if target == "Settings" else "tab_mapping"
        self.dpg.set_value("root_tabs", self.dpg.get_alias_id(tab))
        if self.on_tracking_tab_active:
            self.on_tracking_tab_active(target == "Main")

    def _discard_settings(self):
        self._settings_dirty = False
        self._settings_draft = deepcopy(self.baseline)
        self._render_settings_topic(self.baseline, self._setting_ids["topic"])
        return True

    def _discard_mapping(self):
        self._load_mapping_state()
        self._refresh_mapping_widgets()
        return True

    # Mapping profile and editor model
    def _load_mapping_state(self):
        self._config_path = self._profile_manager.active_profile
        self._config = GestureConfig.load(self._config_path)
        self._mapping_model = MappingModel(self._config)
        self._sync_mapping_state_from_model()
        self._shown_id = self._definitions[0].id if self._definitions else None
        self._mapping_dirty = False

    def _sync_mapping_state_from_model(self):
        """Expose model state to the existing widget callbacks."""
        model = self._mapping_model
        self._config = model.config
        self._definitions = model.definitions
        self._drafts = model.drafts
        self._baseline_drafts = model.baseline_drafts
        self._baseline_definitions = model.baseline_definitions
        self._reset_palm = model.reset_palm
        self._reset_fingers = model.reset_fingers
        self._repeat_values = model.repeat_values
        self._baseline_reset = model.baseline_reset
        self._baseline_repeat = model.baseline_repeat

    def _sync_mapping_model(self):
        """Copy the current widget-facing state into the pure mapping model."""
        model = self._mapping_model
        model.config = self._config
        model.definitions = self._definitions
        model.drafts = self._drafts
        model.baseline_drafts = self._baseline_drafts
        model.baseline_definitions = self._baseline_definitions
        model.reset_palm = self._reset_palm
        model.reset_fingers = self._reset_fingers
        model.repeat_values = self._repeat_values
        model.baseline_reset = self._baseline_reset
        model.baseline_repeat = self._baseline_repeat

    @staticmethod
    def _draft_from_definition(definition):
        return MappingModel.draft_from_definition(definition)

    def _profile_display(self):
        return Path(self._profile_manager.active_profile).stem.replace("_", " ").replace("-", " ").title()

    def _refresh_mapping_widgets(self):
        if not hasattr(self, "_mapping_tags") or not self._mapping_tags:
            return
        dpg = self.dpg
        tags = self._mapping_tags
        dpg.set_value(tags["active_profile"], self._profile_display())
        self._gesture_label_map = self._labels_for_gestures(
            [(i, draft["name"]) for i, draft in self._drafts.items()]
        )
        dpg.configure_item(tags["gesture_selector"], items=list(self._gesture_label_map))
        if self._shown_id in self._drafts:
            dpg.set_value(tags["gesture_selector"], next(
                label for label, gesture_id in self._gesture_label_map.items() if gesture_id == self._shown_id
            ))
            self._show_draft(self._shown_id)
        dpg.set_value(tags["reset_palm"], self._palm_label(self._reset_palm))
        for finger, checkboxes in tags["reset_checks"].items():
            allowed = self._reset_fingers.get(finger, set())
            for position, checkbox in checkboxes.items():
                dpg.set_value(checkbox, position in allowed)
        for key, value in self._repeat_values.items():
            dpg.set_value(tags[key], value)
        dpg.set_value(tags["status"], self._mapping_status)
        dpg.configure_item(tags["save"], enabled=self._mapping_dirty)

    def _show_draft(self, gesture_id):
        if not hasattr(self, "_mapping_tags") or gesture_id not in self._drafts:
            return
        dpg = self.dpg
        tags = self._mapping_tags
        draft = self._drafts[gesture_id]
        dpg.set_value(tags["palm"], self._palm_label(draft["palm"]))
        dpg.set_value(tags["tracked_finger"], draft["tracked_finger"].title() if draft["tracked_finger"] else "None")
        dpg.set_value(tags["commands"], draft["commands"])
        dpg.set_value(tags["delay"], draft["delay"])
        for finger, checks in tags["finger_checks"].items():
            allowed = draft["fingers"].get(finger, set())
            for position, checkbox in checks.items():
                dpg.set_value(checkbox, position in allowed if allowed else False)

    @staticmethod
    def _palm_label(value):
        return next((label for label, key in PALM_OPTIONS.items() if key == value), "Any")

    def _gesture_selected(self, _sender, label):
        self._capture_current_draft()
        self._shown_id = self._gesture_label_map.get(label, self._shown_id)
        self._show_draft(self._shown_id)

    @staticmethod
    def _labels_for_gestures(names):
        labels = {}
        for gesture_id, name in names:
            label, count = name, 2
            while label in labels:
                label = f"{name} ({count})"
                count += 1
            labels[label] = gesture_id
        return labels

    def _mapping_changed(self, *_):
        if not self._shown_id:
            return
        self._capture_current_draft()
        tags = self._mapping_tags
        self._reset_palm = PALM_OPTIONS[self.dpg.get_value(tags["reset_palm"])]
        self._reset_fingers = self._read_finger_checks(tags["reset_checks"], self._reset_fingers)
        try:
            self._repeat_values = {key: self.dpg.get_value(tags[key]) for key in self._repeat_values}
        except (ValueError, TypeError):
            pass
        self._refresh_mapping_dirty()

    def _refresh_mapping_dirty(self):
        self._sync_mapping_model()
        self._mapping_dirty = self._mapping_model.is_dirty()
        self._mapping_status = "Unsaved mapping changes" if self._mapping_dirty else "Gesture mappings saved"
        self.dpg.set_value(self._mapping_tags["status"], self._mapping_status)
        self.dpg.configure_item(self._mapping_tags["save"], enabled=self._mapping_dirty)

    def _read_finger_checks(self, groups, previous):
        """Preserve criteria for categories hidden by the current segment count."""
        result = {}
        for finger, checks in groups.items():
            allowed = set(previous.get(finger, ())) - checks.keys()
            allowed.update(pos for pos, item in checks.items() if self.dpg.get_value(item))
            if allowed:
                result[finger] = allowed
        return result

    def _capture_current_draft(self):
        if not self._shown_id:
            return
        tags = self._mapping_tags
        draft = self._drafts[self._shown_id]
        draft["palm"] = PALM_OPTIONS[self.dpg.get_value(tags["palm"])]
        draft["tracked_finger"] = self.dpg.get_value(tags["tracked_finger"]).lower()
        if draft["tracked_finger"] == "none":
            draft["tracked_finger"] = None
        draft["commands"] = self.dpg.get_value(tags["commands"])
        draft["delay"] = self.dpg.get_value(tags["delay"])
        draft["fingers"] = self._read_finger_checks(tags["finger_checks"], draft["fingers"])

    def _build_mapping_config(self):
        self._capture_current_draft()
        self._sync_mapping_model()
        return self._mapping_model.build_config()

    def _save_mapping(self, *_):
        try:
            config = self._build_mapping_config()
            config.save(self._config_path)
        except (ValueError, OSError) as error:
            self._mapping_status = f"Could not save mappings: {error}"
            self.dpg.set_value(self._mapping_tags["status"], self._mapping_status)
            return False
        self._config = config
        self._definitions = list(config.definitions)
        self._drafts = {item.id: self._draft_from_definition(item) for item in config.definitions}
        self._baseline_drafts = deepcopy(self._drafts)
        self._baseline_definitions = list(self._definitions)
        self._baseline_reset = (self._reset_palm, deepcopy(self._reset_fingers))
        self._baseline_repeat = dict(self._repeat_values)
        self._mapping_dirty = False
        self._mapping_status = "Gesture mappings saved"
        self._refresh_mapping_widgets()
        if self.on_mapping_saved:
            self.on_mapping_saved(config)
        return True

    def _set_segment_count(self, count):
        if not hasattr(self, "_mapping_tags") or not self._mapping_tags:
            return
        # Keep current criteria that remain valid, then rebuild the checkbox matrix.
        self._capture_current_draft()
        finger_parent = self.dpg.get_item_parent("finger_table")
        reset_parent = self.dpg.get_item_parent("reset_table")
        self.dpg.delete_item("finger_table")
        self.dpg.delete_item("reset_table")
        self._mapping_tags["finger_checks"] = {}
        self._mapping_tags["reset_checks"] = {}
        self._render_finger_checks(parent=finger_parent)
        self._render_reset_checks(parent=reset_parent)
        self._refresh_mapping_widgets()

    def is_dirty(self):
        return self._mapping_dirty

    def _show_profile_window(self):
        self._profile_browse_folder = str(self._profile_manager._folder_for(self._profile_manager.source_path))
        self._refresh_profile_list()
        self.dpg.show_item("profile_window")

    def _refresh_profile_list(self):
        folder = Path(self._profile_browse_folder)
        profiles = self._profile_manager.list_profiles(folder)
        self._profile_labels = {path.stem: path for path in profiles}
        self.dpg.configure_item("profile_list", items=list(self._profile_labels))
        self.dpg.set_value("profile_location", str(folder))
        self.dpg.set_value("profile_active_name", self._profile_display())

    def _profile_folder_selected(self, _sender, app_data):
        path = app_data.get("file_path_name") or app_data.get("current_path")
        if path:
            self._profile_browse_folder = path
            self._refresh_profile_list()

    def _profile_file_selected(self, _sender, app_data):
        path = app_data.get("file_path_name") if isinstance(app_data, dict) else None
        if path:
            self._activate_profile(path)

    def _profile_selected(self, _sender, profile):
        path = self._profile_labels.get(profile)
        if path:
            self._activate_profile(path)

    def _activate_profile(self, path, confirmed=False):
        if self._mapping_dirty and not confirmed:
            self._confirm_profile_switch(path)
            return False
        try:
            config = GestureConfig.load(path)
            self._profile_manager.select_profile(path)
        except (ValueError, OSError) as error:
            self._mapping_status = f"Could not load profile: {error}"
            self.dpg.set_value("profile_status", self._mapping_status)
            return False
        self._load_mapping_state()
        self._profile_browse_folder = str(Path(path).parent)
        self.dpg.set_value("profile_status", "")
        if hasattr(self, "_mapping_tags") and self._mapping_tags:
            self._refresh_mapping_widgets()
            self.dpg.set_value(self._mapping_tags["active_profile"], self._profile_display())
            self.dpg.set_value("profile_active_name", self._profile_display())
        if self.on_mapping_saved:
            self.on_mapping_saved(config)
        return True

    def _confirm_profile_switch(self, path):
        dpg = self.dpg
        if dpg.does_item_exist("profile_switch"):
            dpg.delete_item("profile_switch")
        def finish(save):
            if save and not self._save_mapping():
                return
            if self._activate_profile(path, confirmed=True):
                dpg.delete_item("profile_switch")
        with dpg.window(label="Unsaved mappings", tag="profile_switch", modal=True, autosize=True):
            dpg.add_text("Save changes before switching profiles?")
            with dpg.group(horizontal=True):
                self._button("Save", lambda: finish(True), style="primary")
                self._button("Discard", lambda: finish(False), style="danger")
                self._button("Cancel", lambda: dpg.delete_item("profile_switch"))

    def _create_profile(self):
        name = self.dpg.get_value("new_profile_name").strip()
        if not name:
            return
        folder = Path(self._profile_browse_folder)
        path = folder / (name if name.lower().endswith(".json") else f"{name}.json")
        try:
            if Path(name).name != name or any(char in name for char in '<>:"/\\|?*') or name in (".", ".."):
                raise ValueError("Enter a profile name without path separators or reserved characters.")
            if path.exists():
                raise ValueError(f"A profile named {path.stem!r} already exists.")
            config = self._build_mapping_config()
            config.save(path)
            self._activate_profile(path, confirmed=True)
            self.dpg.set_value("new_profile_name", "")
            self._refresh_profile_list()
        except (ValueError, OSError) as error:
            self._mapping_status = f"Could not create profile: {error}"
            self.dpg.set_value(self._mapping_tags["status"], self._mapping_status)
            self.dpg.set_value("profile_status", self._mapping_status)

    def _show_manage_window(self):
        self._capture_current_draft()
        self._managed_definitions = list(self._definitions)
        self._managed_selected_id = self._shown_id
        self._managed_baseline = [(d.id, d.name) for d in self._definitions]
        self._managed_draft_names = {i: draft["name"] for i, draft in self._drafts.items()}
        self._refresh_manage_list()
        self.dpg.show_item("manage_window")

    def _refresh_manage_list(self):
        self._managed_label_map = self._labels_for_gestures(
            [(d.id, d.name) for d in self._managed_definitions]
        )
        values = list(self._managed_label_map)
        self.dpg.configure_item("manage_list", items=values)
        if self._managed_selected_id:
            definition = next((d for d in self._managed_definitions if d.id == self._managed_selected_id), None)
            if definition:
                self.dpg.set_value("manage_list", next(label for label, i in self._managed_label_map.items()
                                                       if i == definition.id))
                self.dpg.set_value("manage_name", definition.name)

    def _managed_selected(self, _sender, name):
        selected_id = self._managed_label_map.get(name)
        definition = next((d for d in self._managed_definitions if d.id == selected_id), None)
        if definition:
            self._managed_selected_id = definition.id
            self.dpg.set_value("manage_name", definition.name)

    def _managed_name_changed(self, _sender, name):
        updated = []
        for definition in self._managed_definitions:
            updated.append(replace(definition, name=name) if definition.id == self._managed_selected_id else definition)
        self._managed_definitions = updated
        if self._managed_selected_id in self._drafts:
            self._drafts[self._managed_selected_id]["name"] = name
            self._refresh_mapping_dirty()
            self._refresh_mapping_widgets()
        self._refresh_manage_list()

    def _manage_create(self):
        from itertools import product
        active = [d.match for d in self._managed_definitions]
        positions = [c.value for c in finger_categories(self.settings.data.finger_segment_count)]
        match = None
        for palm in (None, "facing_camera", "not_facing_camera"):
            for state in product(positions, repeat=len(FINGER_NAMES)):
                candidate = GestureMatch(palm, {name: frozenset((position,)) for name, position in zip(FINGER_NAMES, state)})
                if all(not GestureConfig.matches_can_overlap(candidate, other) for other in active):
                    match = candidate
                    break
            if match:
                break
        if match is None:
            self._mapping_status = "No non-overlapping gesture pattern is available."
            return
        definition = GestureDefinition(
            id=f"gesture_{uuid4().hex[:8]}", name="New Gesture", match=match,
            commands=CommandSequence((CommandStep("key_tap", "a"),)), tracked_finger="index",
        )
        self._managed_definitions.append(definition)
        self._managed_selected_id = definition.id
        self._refresh_manage_list()

    def _manage_delete(self):
        if len(self._managed_definitions) <= 1:
            return
        self._managed_definitions = [d for d in self._managed_definitions if d.id != self._managed_selected_id]
        self._managed_selected_id = self._managed_definitions[0].id
        self._refresh_manage_list()

    def _manage_save_names(self):
        try:
            if any(not d.name.strip() for d in self._managed_definitions):
                raise ValueError("Gesture names cannot be empty.")
            GestureConfig._validate_no_overlaps(self._managed_definitions)
            config = replace(self._config, definitions=tuple(
                replace(d, name=d.name.strip()) for d in self._managed_definitions
            ))
            config.save(self._config_path)
        except (ValueError, OSError) as error:
            self._mapping_status = f"Could not save gestures: {error}"
            self.dpg.set_value("manage_status", self._mapping_status)
            return
        previous_baseline = deepcopy(self._baseline_drafts)
        previous_drafts = deepcopy(self._drafts)
        self._config = config
        self._definitions = list(config.definitions)
        self._managed_definitions = list(config.definitions)
        self._drafts = {}
        self._baseline_drafts = {}
        for definition in config.definitions:
            draft = previous_drafts.get(definition.id, self._draft_from_definition(definition))
            baseline = previous_baseline.get(definition.id, self._draft_from_definition(definition))
            draft["name"] = baseline["name"] = definition.name.strip()
            self._drafts[definition.id] = draft
            self._baseline_drafts[definition.id] = baseline
        self._baseline_definitions = list(self._definitions)
        self._shown_id = self._managed_selected_id
        self._mapping_dirty = (
            self._drafts != self._baseline_drafts
            or self._definitions != self._baseline_definitions
            or self._repeat_values != self._baseline_repeat
            or (self._reset_palm, self._reset_fingers) != self._baseline_reset
        )
        self._refresh_mapping_dirty()
        self._refresh_mapping_widgets()
        self._refresh_manage_list()
        self.dpg.set_value("manage_status", "Gestures saved")
        self._managed_draft_names = {i: draft["name"] for i, draft in self._drafts.items()}
        if self.on_mapping_saved:
            self.on_mapping_saved(config)

    def _close_manage_window(self):
        for gesture_id, name in self._managed_draft_names.items():
            if gesture_id in self._drafts:
                self._drafts[gesture_id]["name"] = name
        self._refresh_mapping_dirty()
        self._refresh_mapping_widgets()
        self.dpg.hide_item("manage_window")
