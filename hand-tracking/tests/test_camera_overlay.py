"""The overlay's camera option, per-platform UI scale, and the macOS overlay logic.

No GUI is created: the overlay window, renderer and AppKit are stand-ins.
"""

import json
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import numpy as np
from PIL import Image

from hand_tracking.backend.settings.overlay_settings import OverlayPosition, OverlaySettings
from hand_tracking.backend.settings.settings_manager import Settings
from hand_tracking.backend.engine.engine import TrackingSwitches
from hand_tracking.backend.engine.runner import EngineSnapshot
from hand_tracking.frontend.application import Application
from hand_tracking.frontend.tracking.hand.debug_panel.live_hand_data import LiveHandData
from hand_tracking.frontend.tracking.hand.overlay.composer import WIDTHS, OverlayComposer
from hand_tracking.frontend.tracking.hand.overlay.hand_tracking_overlay import HandTrackingOverlay

CAMERA = OverlaySettings(content="Camera and stats", size="Small")


class FakeAppearance:
    scale = 1.0
    colors = SimpleNamespace(palette=SimpleNamespace(surface="#202020"))

    def pixels(self, value):
        return round(value * self.scale)

    def refresh(self):
        pass


class FakeRenderer:
    """A 600 x 300 stats panel; counts renders."""

    def __init__(self) -> None:
        self.renders = 0

    def render(self, data, *, style, opacity, max_deviation):
        self.renders += 1
        return Image.new("RGBA", (600, 300), (255, 255, 255, round(opacity * 255)))


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class OverlaySettingsTests(unittest.TestCase):
    def test_older_saved_overlays_show_stats_at_medium(self) -> None:
        loaded = OverlaySettings.from_dict({"style": "Simple", "background_opacity": 0.5})
        self.assertEqual((loaded.content, loaded.size), ("Stats", "Medium"))
        self.assertFalse(loaded.shows_camera)

    def test_camera_choice_survives_saving(self) -> None:
        self.assertEqual(OverlaySettings.from_dict(asdict(CAMERA)), CAMERA)
        self.assertTrue(CAMERA.shows_camera)

    def test_rejects_unknown_choices(self) -> None:
        for changes in ({"content": "Camera"}, {"size": "Huge"}):
            with self.subTest(**changes), self.assertRaises(ValueError):
                OverlaySettings(**changes)


class OverlayComposerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.renderer, self.clock = FakeRenderer(), FakeClock()
        self.composer = OverlayComposer(self.renderer, FakeAppearance(), clock=self.clock)
        self.data = LiveHandData()

    def test_stats_only_is_the_unchanged_stats_panel(self) -> None:
        image = self.composer.compose(self.data, OverlaySettings(), opacity=0.9, max_deviation=75)
        self.assertEqual(image.size, (600, 300))

    def test_camera_sits_above_stats_scaled_to_the_chosen_width(self) -> None:
        self.composer.offer_frame(np.zeros((720, 1280, 3), np.uint8))
        image = self.composer.compose(self.data, CAMERA, opacity=0.9, max_deviation=75)
        width = WIDTHS["Small"]
        camera_height, stats_height, gap = round(width * 720 / 1280), round(300 * width / 600), 4
        self.assertEqual(image.size, (width, camera_height + gap + stats_height))
        self.assertEqual(image.getpixel((0, 0)), (0, 0, 0, 255))  # Camera is opaque

    def test_stats_render_only_when_the_report_changes(self) -> None:
        for _ in range(5):
            self.composer.compose(self.data, CAMERA, opacity=0.9, max_deviation=75)
        self.assertEqual(self.renderer.renders, 1)
        self.composer.compose(LiveHandData(), CAMERA, opacity=0.9, max_deviation=75)
        self.assertEqual(self.renderer.renders, 2)

    def test_camera_redraws_are_capped(self) -> None:
        frame = np.zeros((10, 10, 3), np.uint8)
        self.assertTrue(self.composer.offer_frame(frame))
        self.clock.now += 0.01
        self.assertFalse(self.composer.offer_frame(frame))
        self.clock.now += 0.03
        self.assertTrue(self.composer.offer_frame(frame))


class OverlayCameraTests(unittest.TestCase):
    def make_overlay(self, preferences=OverlaySettings()):
        self.window = Mock(appearance=FakeAppearance())
        self.saved = []
        overlay = HandTrackingOverlay(
            None, max_deviation=75, preferences=preferences,
            on_save=self.saved.append, window_factory=lambda _parent: self.window,
        )
        return overlay

    def test_workspace_switch_applies_and_saves_immediately(self) -> None:
        overlay = self.make_overlay()
        overlay.enable()
        self.assertFalse(overlay.shows_camera)
        overlay.set_content(content="Camera and stats")
        self.assertTrue(overlay.shows_camera)
        self.assertEqual(self.saved[-1].content, "Camera and stats")

    def test_frames_redraw_only_a_camera_overlay(self) -> None:
        frame = np.zeros((10, 10, 3), np.uint8)
        overlay = self.make_overlay()
        overlay.enable()
        self.window.redraw.reset_mock()
        overlay.show_frame(frame)
        self.window.redraw.assert_not_called()
        overlay.set_content(content="Camera and stats")
        self.window.redraw.reset_mock()
        overlay.show_frame(frame)
        self.window.redraw.assert_called_once()


class FrameRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = Application.__new__(Application)
        self.app.engine = MagicMock()
        self.app.preview = Mock()
        self.app.hand_tracking = Mock(preview_active=False)
        self.app._preview_hidden = False
        self.app._seen_sequence = 0
        self.app._hand_reports = []
        self.app._show_statuses = Mock()
        self.app._refresh_gesture_display = Mock()
        self.sequence = 0

    def snapshot(self):
        self.sequence += 1
        result = SimpleNamespace(frame=object(), hand_reports=[])
        return EngineSnapshot(self.sequence, result, TrackingSwitches())

    def test_camera_overlay_takes_the_frames_and_hides_the_preview_once(self) -> None:
        self.app.hand_tracking.shows_camera = True
        self.app._display(self.snapshot())
        self.app._display(self.snapshot())
        self.app.preview.set_visible.assert_called_once_with(False)
        self.app.preview.show.assert_not_called()
        self.assertEqual(self.app.hand_tracking.show_frame.call_count, 2)

        self.app.hand_tracking.shows_camera = False
        self.app._display(self.snapshot())
        self.app.preview.set_visible.assert_called_with(True)
        self.app.preview.show.assert_called_once()

    def test_an_already_displayed_snapshot_is_not_shown_again(self) -> None:
        self.app.hand_tracking.shows_camera = False
        snapshot = self.snapshot()
        self.app._display(snapshot)
        self.app._display(snapshot)
        self.app.preview.show.assert_called_once()


class PerPlatformUiScaleTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "settings.json"

    def test_a_windows_scale_never_reaches_macos(self) -> None:
        # Files from before per-platform scales were written on Windows.
        self.path.write_text(json.dumps({"ui_scale": "150%"}), encoding="utf-8")
        self.assertEqual(Settings(str(self.path), platform_key="Windows").data.ui_scale, "150%")
        self.assertEqual(Settings(str(self.path), platform_key="macOS").data.ui_scale, "Auto")

    def test_each_platform_keeps_its_own_scale(self) -> None:
        self.path.write_text(json.dumps({"ui_scale": "150%"}), encoding="utf-8")
        Settings(str(self.path), platform_key="macOS").update_fields({"ui_scale": "125%"})
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(saved["ui_scales"], {"Windows": "150%", "macOS": "125%"})
        self.assertNotIn("ui_scale", saved)


def rect(x, y, width, height):
    return SimpleNamespace(origin=SimpleNamespace(x=x, y=y), size=SimpleNamespace(width=width, height=height))


class FakePanel:
    def __init__(self) -> None:
        self.calls = {}
        self.frame_rect = rect(0, 0, 1, 1)

    def __getattr__(self, name):
        def record(*args):
            self.calls[name] = args
            if name == "setFrame_display_":
                self.frame_rect = args[0]
        return record

    def frame(self):
        return self.frame_rect


def fake_appkit():
    """Enough of AppKit for MacOverlayWindow: one 1440 x 900 screen with a 25-point menu bar."""
    appkit = ModuleType("AppKit")
    for name in (
        "NSWindowStyleMaskBorderless", "NSWindowStyleMaskNonactivatingPanel", "NSBackingStoreBuffered",
        "NSStatusWindowLevel", "NSWindowCollectionBehaviorCanJoinAllSpaces",
        "NSWindowCollectionBehaviorFullScreenAuxiliary", "NSWindowCollectionBehaviorStationary",
        "NSWindowCollectionBehaviorIgnoresCycle", "NSImageScaleAxesIndependently",
    ):
        setattr(appkit, name, 1)
    appkit.NSMakeRect = rect
    appkit.panel = FakePanel()
    appkit.NSPanel = SimpleNamespace(alloc=lambda: SimpleNamespace(
        initWithContentRect_styleMask_backing_defer_=lambda *args: appkit.panel,
    ))
    appkit.NSImageView = SimpleNamespace(alloc=lambda: SimpleNamespace(initWithFrame_=lambda frame: Mock()))
    appkit.NSColor = SimpleNamespace(clearColor=lambda: "clear")
    appkit.NSData = SimpleNamespace(dataWithBytes_length_=lambda data, length: data)
    appkit.NSImage = SimpleNamespace(alloc=lambda: SimpleNamespace(initWithData_=lambda data: Mock()))
    screen = SimpleNamespace(frame=lambda: rect(0, 0, 1440, 900), visibleFrame=lambda: rect(0, 0, 1440, 875))
    appkit.NSScreen = SimpleNamespace(mainScreen=lambda: screen, screens=lambda: [screen])
    return appkit


class MacOverlayWindowTests(unittest.TestCase):
    """The AppKit calls themselves can only be checked on a Mac; this checks their inputs."""

    def setUp(self) -> None:
        self.appkit = fake_appkit()
        modules = patch.dict(sys.modules, {"AppKit": self.appkit})
        modules.start()
        self.addCleanup(modules.stop)
        theme = patch("hand_tracking.frontend.components.overlays.macos_window.ThemeMetrics", Mock())
        theme.start()
        self.addCleanup(theme.stop)
        from hand_tracking.frontend.components.overlays.macos_window import MacOverlayWindow

        self.window = MacOverlayWindow(None)
        self.window.set_renderer(lambda opacity: Image.new("RGBA", (200, 100)))
        self.panel = self.appkit.panel

    def test_panel_is_click_through_and_floats_over_full_screen_apps(self) -> None:
        self.assertEqual(self.panel.calls["setIgnoresMouseEvents_"], (True,))
        self.assertEqual(self.panel.calls["setOpaque_"], (False,))
        self.assertIn("setCollectionBehavior_", self.panel.calls)

    def test_first_show_goes_to_the_top_right_in_appkit_coordinates(self) -> None:
        self.window.show()
        self.assertEqual(self.window.position, OverlayPosition(1440 - 200 - 20, 25))
        placed = self.panel.calls["setFrame_display_"][0]
        # AppKit's y counts up from the bottom: 900 - top 25 - height 100.
        self.assertEqual((placed.origin.x, placed.origin.y), (1220, 775))
        self.assertIn("orderFrontRegardless", self.panel.calls)

    def test_repositioning_takes_the_mouse_then_reports_the_dragged_position(self) -> None:
        self.window.show()
        moved = []
        self.window.on_position_changed = moved.append
        self.window.set_repositioning(True)
        self.assertEqual(self.panel.calls["setIgnoresMouseEvents_"], (False,))
        self.assertEqual(self.panel.calls["setMovableByWindowBackground_"], (True,))
        self.panel.frame_rect = rect(100, 600, 200, 100)  # Dragged by the user
        self.window.set_repositioning(False)
        self.assertEqual(self.panel.calls["setIgnoresMouseEvents_"], (True,))
        self.assertEqual(moved, [OverlayPosition(100, 900 - 600 - 100)])


if __name__ == "__main__":
    unittest.main()
