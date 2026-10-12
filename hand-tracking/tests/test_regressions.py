"""Regression checks for UI drafts and profile persistence without hardware."""

import sys
import importlib.util
import tempfile
import time
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Geometry only needs the frame aspect here, not a camera driver.
with patch.dict(sys.modules, {"camera": SimpleNamespace(Camera=SimpleNamespace(aspect=1.0))}):
    from gui.control_window import ControlWindow
    from gui.scheduler import CallbackScheduler
    from gestures.gesture_config import GestureConfig, RepeatSettings
    from settings.settings_manager import SettingsData


class Widgets:
    def __init__(self):
        self.values = {}
        self.configs = {}
        self.created = 0

    def get_value(self, item):
        return self.values.get(item)

    def set_value(self, item, value):
        self.values[item] = value

    def configure_item(self, item, **values):
        self.configs.setdefault(item, {}).update(values)

    def does_item_exist(self, item):
        return item in self.values

    def add_progress_bar(self, **kwargs):
        self.created += 1
        tag = f"bar_{self.created}"
        self.values[tag] = kwargs.get("default_value", 0)
        return tag

    def hide_item(self, item):
        self.configure_item(item, show=False)

    def show_item(self, item):
        self.configure_item(item, show=True)

    def get_callback_queue(self):
        return []

    def run_callbacks(self, jobs):
        pass


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "profile.json"
        self.config = GestureConfig.load(ROOT / "gestures/default_gesture_profile.json")
        self.config.save(self.path)
        ui = self.ui = ControlWindow.__new__(ControlWindow)
        ui.dpg = Widgets()
        ui.settings = SimpleNamespace(data=SettingsData())
        ui._profile_manager = SimpleNamespace(active_profile=str(self.path))
        ui._profile_manager.select_profile = lambda path: setattr(ui._profile_manager, "active_profile", str(path))
        ui._profile_browse_folder = self.temp.name
        ui._mapping_tags = {"status": "status", "save": "save", "active_profile": "active_profile"}
        ui._mapping_status = "Loaded"
        ui._refresh_mapping_widgets = lambda: None
        ui._refresh_manage_list = lambda: None
        ui._refresh_profile_list = lambda: None
        ui._capture_current_draft = lambda: None
        ui.on_mapping_saved = None
        ui._load_mapping_state()

    def test_new_gesture_can_be_saved_and_deleted(self):
        ui = self.ui
        ui._show_manage_window()
        ui._manage_create()
        new_id = ui._managed_selected_id
        ui._manage_save_names()
        self.assertIn(new_id, ui._drafts)
        self.assertIn(new_id, ui._baseline_drafts)
        self.assertIn(new_id, [d.id for d in GestureConfig.load(self.path).definitions])
        ui._manage_delete()
        ui._manage_save_names()
        self.assertNotIn(new_id, ui._drafts)
        self.assertNotIn(new_id, ui._baseline_drafts)

    def test_saving_names_preserves_pending_mapping_edits(self):
        ui = self.ui
        selected = ui._shown_id
        ui._drafts[selected]["delay"] += 125
        ui._show_manage_window()
        ui._managed_name_changed(None, "Renamed")
        ui._manage_save_names()
        self.assertTrue(ui._mapping_dirty)
        self.assertNotEqual(ui._drafts[selected]["delay"], ui._baseline_drafts[selected]["delay"])
        saved = next(d for d in GestureConfig.load(self.path).definitions if d.id == selected)
        self.assertEqual(saved.name, "Renamed")
        self.assertEqual(saved.commands.delay_ms_between_steps, ui._baseline_drafts[selected]["delay"])

    def test_closing_manager_discards_uncommitted_names(self):
        ui = self.ui
        original = ui._drafts[ui._shown_id]["name"]
        ui._show_manage_window()
        ui._managed_name_changed(None, "Temporary name")
        ui._close_manage_window()
        self.assertEqual(ui._drafts[ui._shown_id]["name"], original)
        self.assertFalse(ui._mapping_dirty)

    def test_mapping_save_updates_repeat_and_reset_baselines(self):
        ui = self.ui
        ui._repeat_values["initial_displacement"] = 0.123
        ui._reset_palm = "facing_camera"
        self.assertTrue(ui._save_mapping())
        ui._refresh_mapping_dirty()
        self.assertFalse(ui._mapping_dirty)
        self.assertAlmostEqual(GestureConfig.load(self.path).repeat_settings.initial_displacement, 0.123)

    def test_profile_creation_never_overwrites_existing_file(self):
        original = self.path.read_bytes()
        self.ui.dpg.values["new_profile_name"] = "profile"
        self.ui._create_profile()
        self.assertEqual(self.path.read_bytes(), original)
        self.assertIn("already exists", self.ui._mapping_status)

    def test_new_profile_is_created_and_activated(self):
        self.ui.dpg.values["new_profile_name"] = "new_profile"
        self.ui._create_profile()
        created = Path(self.temp.name) / "new_profile.json"
        self.assertTrue(created.is_file())
        self.assertEqual(self.ui._config_path, str(created))
        self.assertEqual(GestureConfig.load(created), self.config)

    def test_hidden_finger_criteria_survive_edits(self):
        ui = self.ui
        ui.dpg.values["straight_check"] = True
        selected = ui._read_finger_checks({"index": {"straight": "straight_check"}},
                                         {"index": {"very_curled"}})
        self.assertEqual(selected["index"], {"straight", "very_curled"})

    def test_discard_settings_restores_draft_from_advanced_topic(self):
        ui = self.ui
        ui.baseline = SettingsData()
        ui._settings_draft = replace(ui.baseline, theme="Dark")
        ui._setting_ids = {"topic": "Advanced"}
        ui._render_settings_topic = lambda *_: None
        ui._discard_settings()
        self.assertEqual(ui._settings_draft, ui.baseline)

    def test_preview_uses_draft_thresholds_and_reuses_widgets(self):
        ui = self.ui
        ui._setting_ids = {"preview": "preview", "preview_bars": "group", "preview_enabled": True}
        ui.dpg.values.update(preview="", group=None)
        ui._settings_draft = SettingsData(finger_classification_thresholds=[30, 45, 75])
        ui._preview_status = "Live"
        ui._preview_fingers = {"index": SimpleNamespace(deviation=20)}
        ui._px = lambda n: n
        ui._render_preview()
        ui._render_preview()
        self.assertEqual(ui.dpg.created, 5)
        index_bar = ui._setting_ids["preview_items"]["index"]
        self.assertIn("Straight", ui.dpg.configs[index_bar]["overlay"])

    def test_invalid_commands_cannot_replace_a_valid_profile(self):
        original = self.path.read_bytes()
        first = self.config.definitions[0]
        invalid = replace(first, commands=replace(first.commands, delay_ms_between_steps=-1))
        config = replace(self.config, definitions=(invalid, *self.config.definitions[1:]))
        with self.assertRaises(ValueError):
            config.save(self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_nonfinite_repeat_values_are_rejected(self):
        for value in (float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                RepeatSettings.from_dict({"distance_threshold": value})

    def test_duplicate_names_have_distinct_selectable_labels(self):
        labels = ControlWindow._labels_for_gestures([("one", "Same"), ("two", "Same")])
        self.assertEqual(set(labels.values()), {"one", "two"})
        self.assertEqual(len(labels), 2)

    def test_switching_profile_requires_a_decision_for_unsaved_mappings(self):
        ui = self.ui
        ui._mapping_dirty = True
        pending = []
        ui._confirm_profile_switch = pending.append
        selected = Path(self.temp.name) / "other.json"
        self.assertFalse(ui._activate_profile(selected))
        self.assertEqual(pending, [selected])
        self.assertEqual(ui._config_path, str(self.path))

    def test_application_callbacks_do_not_wait_for_every_ui_render(self):
        ui = self.ui
        ui._running = True
        ui._close_pending = False
        ui._scheduler = CallbackScheduler()
        rendered, processed = [], []
        ui.dpg.is_dearpygui_running = lambda: ui._running
        ui.dpg.stop_dearpygui = lambda: None
        ui.dpg.render_dearpygui_frame = lambda: rendered.append(True)
        clock = iter(n / 1000 for n in range(1000))
        def callback():
            processed.append(True)
            if len(processed) == 10:
                ui.quit()
            else:
                ui.after(1, callback)
        with patch.object(time, "monotonic", side_effect=lambda: next(clock)), \
                patch.object(time, "sleep"):
            ui.after(0, callback)
            ui.run()
        self.assertEqual(len(processed), 10)
        self.assertLess(len(rendered), 10)

    def test_failed_camera_waits_and_allows_retrying_same_device(self):
        class Capture:
            def isOpened(self):
                return True
            def set(self, *_):
                pass
            def get(self, *_):
                return 720
            def read(self):
                return False, None
            def release(self):
                pass
        opened = []
        def open_camera(index):
            opened.append(index)
            return Capture()
        cv2 = SimpleNamespace(VideoCapture=open_camera, CAP_PROP_FPS=1,
                              CAP_PROP_FRAME_WIDTH=2, CAP_PROP_FRAME_HEIGHT=3,
                              CAP_PROP_BUFFERSIZE=4)
        spec = importlib.util.spec_from_file_location("review_camera", ROOT / "camera.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"cv2": cv2}):
            spec.loader.exec_module(module)
        camera = module.Camera(camera_index=1)
        self.addCleanup(camera.release)
        def wait_for(predicate):
            deadline = time.monotonic() + 1
            while not predicate() and time.monotonic() < deadline:
                time.sleep(.005)
            self.assertTrue(predicate())
        wait_for(lambda: camera.status()[0] == "failed")
        time.sleep(.02)
        self.assertEqual(opened, [1])
        self.assertIsNone(camera.read())
        camera.request_switch(1)
        wait_for(lambda: len(opened) == 2 and camera.status()[0] == "failed")
        self.assertEqual(opened, [1, 1])

    def test_queued_repeat_fires_after_movement_stops_and_respects_pause(self):
        spec = importlib.util.spec_from_file_location("review_gesture_handler", ROOT / "gesture_handler.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {
            "camera": SimpleNamespace(Camera=SimpleNamespace(aspect=1.0)),
            "custom_overlay.invoker_overlay": SimpleNamespace(InvokerOverlay=object),
            "input.command_executor": SimpleNamespace(CommandExecutor=object),
        }):
            spec.loader.exec_module(module)
        handler = module.GestureHandler.__new__(module.GestureHandler)
        fired = []
        handler.command_executor = SimpleNamespace(update=lambda: None)
        handler._active_gesture = "gesture"
        handler.config = SimpleNamespace(repeat_settings=RepeatSettings(min_interval_seconds=0))
        handler.definitions_by_id = {"gesture": object()}
        handler._pending_repeats = [(0.2, 0.3)]
        handler._repeat_markers = []
        handler._last_repeat_time = 0
        handler._repeat_count = 0
        handler._press = fired.append
        handler.update(allow_repeats=False)
        self.assertFalse(fired)
        handler.update()
        self.assertEqual(len(fired), 1)
        self.assertEqual(handler._repeat_markers, [(0.2, 0.3)])


if __name__ == "__main__":
    unittest.main()
