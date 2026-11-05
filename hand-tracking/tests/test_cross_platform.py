"""Saved paths and the preview choice behave correctly on Windows and macOS.

macOS is simulated by replacing the ``os`` module the path helpers consult,
so these tests run on either system.
"""

import ast
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from hand_tracking.backend.common import project_paths
from hand_tracking.backend.common.project_paths import (
    PROJECT_ROOT, is_foreign_path, portable_path, resolve_saved_path,
)
from hand_tracking.backend.gestures.gesture_config import DEFAULT_GESTURE_CONFIG, DEFAULT_GESTURE_PROFILE_DIR
from hand_tracking.backend.gestures.profile_manager import GestureProfileManager
from hand_tracking.backend.landmarker.model_asset import DEFAULT_MODEL_PATH
from hand_tracking.backend.settings.settings_manager import Settings
from hand_tracking.frontend.platforms.base import Platform
from hand_tracking.frontend.platforms.macos import MacPlatform
from hand_tracking.frontend.platforms.detect import current_platform
from hand_tracking.frontend.platforms.windows import WindowsPlatform
from hand_tracking.frontend.tk_camera_preview import TkCameraPreview

WINDOWS_MODEL = r"C:\Users\someone\hand-tracking\tasks\hand_landmarker.task"


def on_macos():
    return patch.object(project_paths, "os", SimpleNamespace(name="posix"))


class SavedPathTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def test_paths_from_the_other_system_are_recognized(self) -> None:
        self.assertTrue(is_foreign_path(WINDOWS_MODEL, windows=False))
        self.assertTrue(is_foreign_path("/Users/someone/model.task", windows=True))
        for relative in ("tasks/hand_landmarker.task", "gesture_profiles"):
            self.assertFalse(is_foreign_path(relative, windows=False))
            self.assertFalse(is_foreign_path(relative, windows=True))
        self.assertFalse(is_foreign_path("//server/share/model.task", windows=True))

    def test_saved_text_resolves_inside_the_project_or_falls_back(self) -> None:
        default = PROJECT_ROOT / "fallback"
        self.assertEqual(resolve_saved_path(WINDOWS_MODEL, default, windows=False), default)
        self.assertEqual(
            resolve_saved_path("gesture_profiles/a.json", default, windows=False),
            PROJECT_ROOT / "gesture_profiles" / "a.json",
        )

    def test_project_paths_are_saved_relative_with_forward_slashes(self) -> None:
        self.assertEqual(portable_path(PROJECT_ROOT / "tasks" / "hand_landmarker.task"), "tasks/hand_landmarker.task")
        outside = self.directory / "model.task"
        self.assertEqual(portable_path(outside), str(outside.resolve()))

    def test_windows_model_path_falls_back_to_the_bundled_model_on_macos(self) -> None:
        path = self.directory / "settings.json"
        path.write_text(json.dumps({"hand_landmarker_model_path": WINDOWS_MODEL}), encoding="utf-8")
        with on_macos():
            settings = Settings(str(path))
        self.assertEqual(settings.data.hand_landmarker_model_path, DEFAULT_MODEL_PATH)

    def test_settings_save_the_model_path_relative_to_the_project(self) -> None:
        path = self.directory / "settings.json"
        settings = Settings(str(path))
        settings.update_fields({"hand_landmarker_model_path": str(PROJECT_ROOT / "tasks" / "hand_landmarker.task")})
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["hand_landmarker_model_path"], "tasks/hand_landmarker.task")

    def test_windows_profile_selection_falls_back_without_creating_folders_on_macos(self) -> None:
        selection = self.directory / "selection.json"
        selection.write_text(json.dumps({
            "source_path": r"C:\Users\someone\hand-tracking\gesture_profiles",
            "active_profile": r"C:\Users\someone\hand-tracking\gesture_profiles\invoker_profile.json",
        }), encoding="utf-8")
        before = set(Path.cwd().iterdir())
        with on_macos():
            manager = GestureProfileManager(selection)
        self.assertEqual(Path(manager.source_path), DEFAULT_GESTURE_PROFILE_DIR)
        self.assertEqual(Path(manager.active_profile).parent, DEFAULT_GESTURE_PROFILE_DIR)
        self.assertEqual(set(Path.cwd().iterdir()), before, "a folder named after the Windows path was created")
        saved = json.loads(selection.read_text(encoding="utf-8"))
        self.assertEqual(saved["source_path"], "gesture_profiles")
        self.assertTrue(saved["active_profile"].startswith("gesture_profiles/"))


class PlatformTests(unittest.TestCase):
    def test_each_system_gets_its_platform(self) -> None:
        self.assertIsInstance(current_platform("win32"), WindowsPlatform)
        self.assertIsInstance(current_platform("darwin"), MacPlatform)
        self.assertIs(type(current_platform("linux")), Platform)

    def test_macos_uses_portable_implementations(self) -> None:
        mac = MacPlatform()
        preview = mac.create_camera_preview()
        self.assertIsInstance(preview, TkCameraPreview)
        preview.show(object())  # Before attach there is no window to draw in.
        preview.close()
        self.assertFalse(mac.create_title_bar_style().available)
        self.assertEqual(mac.default_camera_index, 0)
        with self.assertRaisesRegex(RuntimeError, "not available on Portable"):
            Platform().create_overlay_window(None)

    def test_components_never_check_the_operating_system_themselves(self) -> None:
        allowed = {
            Path("frontend/platforms/detect.py"),          # Chooses the Platform
            Path("frontend/core/win32.py"),                # Windows API binding guard
            Path("backend/common/project_paths.py"),       # Where a saved path was written
        }
        package = PROJECT_ROOT / "hand_tracking"
        found = []
        for source in package.rglob("*.py"):
            relative = source.relative_to(package)
            if relative in allowed:
                continue
            tree = ast.parse(source.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                        and (node.value.id, node.attr) in {("sys", "platform"), ("os", "name")}):
                    found.append(f"{relative}:{node.lineno}")
        self.assertEqual(found, [], "use the Platform object instead")


if __name__ == "__main__":
    unittest.main()
