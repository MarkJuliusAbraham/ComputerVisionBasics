"""Dear PyGui panel objects used by the control window.

Panels own construction of their section of the interface.  They intentionally
delegate application actions back to the window, which remains the boundary
between UI events and the camera/gesture pipeline.
"""

from gestures.finger_classifier import finger_categories

from gui.panel_constants import FINGER_NAMES, MUTED, PALM_OPTIONS


class MainPanel:
    def __init__(self, window):
        self.window = window

    def build(self):
        w = self.window
        dpg = w.dpg
        w._heading("Live tracking")
        with dpg.group(horizontal=True):
            w._main_ids["pause"] = w._button("Pause tracking", w._toggle_tracking, style="primary")
            w._button("Restart", w._request_restart)
            w._button("Exit", w._request_close, style="danger")
        w._spacer(4)
        with dpg.child_window(auto_resize_y=True, border=True, no_scrollbar=True, no_scroll_with_mouse=True):
            w._caption("Camera device")
            with dpg.group(horizontal=True):
                w._main_ids["camera_picker"] = dpg.add_combo(
                    [str(i) for i in range(10)], default_value=str(w._camera_index),
                    width=w._px(90), tag="camera_picker",
                )
                w._main_ids["camera_switch"] = w._button("Switch camera", w._switch_camera)
            w._main_ids["camera_status"] = dpg.add_text("Opening camera…")
        w._spacer(4)
        w._caption("Live gesture data")
        w._main_ids["tracking_status"] = dpg.add_text("Waiting for camera…")
        with dpg.table(header_row=False, policy=dpg.mvTable_SizingStretchSame):
            dpg.add_table_column()
            dpg.add_table_column()
            with dpg.table_row():
                for handedness in ("Left", "Right"):
                    with dpg.child_window(width=-1, auto_resize_y=True, border=True,
                                          no_scrollbar=True, no_scroll_with_mouse=True):
                        w._heading(f"{handedness} hand")
                        palm = dpg.add_text("Palm: —")
                        command = dpg.add_text("Command: —")
                        dpg.add_separator()
                        fingers = {}
                        with dpg.table(header_row=False):
                            dpg.add_table_column(width_fixed=True, init_width_or_weight=w._px(80))
                            dpg.add_table_column(width_stretch=True, init_width_or_weight=1.0)
                            dpg.add_table_column(width_fixed=True, init_width_or_weight=w._px(84))
                            for name in FINGER_NAMES:
                                with dpg.table_row():
                                    dpg.add_text(name.title())
                                    bar = dpg.add_progress_bar(default_value=0, width=-1,
                                                               height=w._px(22), overlay="—")
                                    score = dpg.add_text("—")
                                    fingers[name] = (bar, score)
                    w._main_ids[handedness] = {
                        "palm": palm, "command": command, "fingers": fingers,
                    }
        w._main_ids["hand_panel_group"] = None


class SettingsPanel:
    def __init__(self, window):
        self.window = window

    def build(self, data):
        w = self.window
        dpg = w.dpg
        with dpg.group(horizontal=True):
            w._button("Apply changes", w._apply_settings, style="primary")
            w._setting_ids["status"] = dpg.add_text("")
        with dpg.group(horizontal=True):
            with dpg.child_window(width=w._px(200), height=-1, border=True,
                                  no_scrollbar=True, no_scroll_with_mouse=True):
                w._caption("Settings")
                w._setting_ids["topic"] = "Tracking"
                w._setting_ids["nav"] = {}
                for topic in ("Tracking", "Appearance", "Advanced"):
                    w._setting_ids["nav"][topic] = dpg.add_selectable(
                        label=topic, default_value=topic == "Tracking",
                        callback=w._select_settings_topic, user_data=topic,
                        span_columns=True,
                    )
            with dpg.child_window(width=-1, height=-1, border=True):
                w._setting_ids["content"] = dpg.add_group()
        w._render_settings_topic(data, "Tracking")


class MappingPanel:
    def __init__(self, window):
        self.window = window

    def build(self):
        w = self.window
        dpg = w.dpg
        w._mapping_tags = {}
        with dpg.child_window(width=-1, auto_resize_y=True, border=True,
                              no_scrollbar=True, no_scroll_with_mouse=True):
            w._caption("Active gesture profile")
            w._mapping_tags["active_profile"] = w._heading(w._profile_display())
            with dpg.group(horizontal=True):
                w._button("More profiles", w._show_profile_window)
                w._mapping_tags["save"] = w._button("Save mappings", w._save_mapping, style="primary")
                w._mapping_tags["status"] = dpg.add_text(w._mapping_status)
        w._spacer(2)
        with dpg.tab_bar():
            with dpg.tab(label="  Gesture  "):
                w._spacer(4)
                w._heading("Gesture")
                with dpg.group(horizontal=True):
                    w._mapping_tags["gesture_selector"] = dpg.add_combo(
                        [], width=w._px(260), callback=w._gesture_selected
                    )
                    w._button("Manage gestures", w._show_manage_window)
                dpg.add_separator()
                w._mapping_tags["palm"] = dpg.add_combo(
                    list(PALM_OPTIONS), label="Palm orientation", width=w._px(230),
                    callback=w._mapping_changed,
                )
                w._mapping_tags["tracked_finger"] = dpg.add_combo(
                    ["None", *(name.title() for name in FINGER_NAMES)],
                    label="Tracked fingertip", width=w._px(230), callback=w._mapping_changed,
                )
                w._spacer(4)
                w._caption("Allowed finger positions (leave all unchecked for Any)")
                w._mapping_tags["finger_checks"] = {}
                w._render_finger_checks(parent=dpg.last_container())
            with dpg.tab(label="  Commands  "):
                w._spacer(4)
                w._heading("Command sequence")
                w._mapping_tags["commands"] = dpg.add_input_text(
                    label="Keys, one character per step separated by commas",
                    width=-w._px(340), callback=w._mapping_changed,
                )
                w._mapping_tags["delay"] = dpg.add_input_int(
                    label="Delay between steps (ms)", min_value=0, min_clamped=True,
                    width=w._px(220), callback=w._mapping_changed,
                )
            with dpg.tab(label="  Reset  "):
                w._spacer(4)
                w._heading("Reset gesture")
                w._mapping_tags["reset_palm"] = dpg.add_combo(
                    list(PALM_OPTIONS), label="Palm orientation", width=w._px(230),
                    callback=w._mapping_changed,
                )
                w._spacer(4)
                w._caption("Require each finger to match one of the checked positions")
                w._mapping_tags["reset_checks"] = {}
                w._render_reset_checks(parent=dpg.last_container())
            with dpg.tab(label="  Repeat  "):
                w._spacer(4)
                w._heading("Repeat behavior")
                dpg.add_text("Initial displacement is the dead zone before path distance begins accumulating.",
                             color=MUTED, wrap=0)
                w._spacer(4)
                for label, key, default, minimum, maximum, step in (
                    ("Initial displacement", "initial_displacement", 0.03, 0, .5, .01),
                    ("Path distance between repeats", "distance_threshold", .09, .01, 1, .01),
                    ("Minimum repeat interval (ms)", "min_interval_ms", 50, 0, 2000, 10),
                    ("Maximum repeats per gesture", "max_repeats", 2, 0, 20, 1),
                ):
                    create_input = dpg.add_input_int if key == "max_repeats" else dpg.add_input_float
                    w._mapping_tags[key] = create_input(
                        label=label, default_value=default, min_value=minimum,
                        max_value=maximum, width=w._px(270), step=step,
                        callback=w._mapping_changed,
                    )
        w._refresh_mapping_widgets()
        self._build_profile_window()
        self._build_manage_window()

    def _build_profile_window(self):
        w = self.window
        dpg = w.dpg
        with dpg.window(label="Gesture Profiles", tag="profile_window", show=False,
                        modal=True, width=w._px(620), height=w._px(550)):
            dpg.add_text("Choose a folder or a profile file")
            with dpg.group(horizontal=True):
                dpg.add_input_text(tag="profile_location", default_value=w._profile_manager.source_path,
                                   readonly=True, width=-w._px(250))
                w._button("Browse folder", lambda: dpg.show_item("profile_folder_dialog"))
                w._button("Choose file", lambda: dpg.show_item("profile_file_dialog"))
            w._caption("Available profiles")
            dpg.add_listbox([], tag="profile_list", num_items=8, width=-1, callback=w._profile_selected)
            w._caption("Active profile")
            dpg.add_text(w._profile_display(), tag="profile_active_name")
            dpg.add_text("", tag="profile_status", wrap=0)
            with dpg.group(horizontal=True):
                dpg.add_input_text(tag="new_profile_name", hint="New profile name", width=-w._px(150))
                w._button("Create profile", w._create_profile, style="primary")
            w._button("Close", lambda: dpg.hide_item("profile_window"))

    def _build_manage_window(self):
        w = self.window
        dpg = w.dpg
        with dpg.window(label="Manage Gestures", tag="manage_window", show=False,
                        modal=True, width=w._px(560), height=w._px(520),
                        on_close=w._close_manage_window):
            dpg.add_text("Gesture names are saved separately from mapping edits.", color=MUTED)
            dpg.add_listbox([], tag="manage_list", num_items=10, width=-1, callback=w._managed_selected)
            dpg.add_input_text(tag="manage_name", label="Name", width=-w._px(60),
                               callback=w._managed_name_changed)
            dpg.add_text("", tag="manage_status", wrap=0)
            with dpg.group(horizontal=True):
                w._button("Create", w._manage_create)
                w._button("Delete", w._manage_delete, style="danger")
                w._button("Save names", w._manage_save_names, style="primary")
                w._button("Close", w._close_manage_window)
