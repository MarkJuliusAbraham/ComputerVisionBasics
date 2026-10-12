"""Feed mock detections through the application into real Tkinter widgets.

Run from hand-tracking:
    python -m unittest discover -s tests -p test_gesture_reporting.py -v

No camera, MediaPipe model, keyboard input, or saved configuration is used.
"""

import sys
import tkinter as tk
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class HardwareInputForbidden:
    def __init__(self):
        raise AssertionError("These tests must never create real keyboard input")


# Import the real application and widgets without requiring hardware libraries.
# The executor below uses a recording simulator, never the OS keyboard backend.
with patch.dict(sys.modules, {
    "cv2": SimpleNamespace(),
    "mediapipe": SimpleNamespace(),
    "camera": SimpleNamespace(Camera=SimpleNamespace(aspect=1.0)),
    "input.input_simulator": SimpleNamespace(InputSimulator=HardwareInputForbidden),
}):
    import application as application_module
    import gesture_handler as handler_module
    import hand_tracker as tracker_module
    from application import Application
    from gesture_handler import GestureHandler
    from gestures.detector import GestureState
    from gestures.finger_classifier import FingerPosition, FingerState
    from gestures.gesture_config import (
        CommandSequence, CommandStep, GestureConfig, GestureDefinition, GestureMatch,
    )
    from gestures.palm_detector import PalmPosition
    from gui_tkinter.components.theme import gesture_classification_color
    from hand_tracker import HandTracker
    from input.command_executor import CommandExecutor
    from settings.settings_manager import SettingsData


class MockClock:
    def __init__(self):
        self.now = 10.0

    def advance(self, seconds):
        self.now += seconds


class RecordingInput:
    def __init__(self):
        self.events = []

    def press(self, key):
        self.events.append(("press", key))

    def release(self, key):
        self.events.append(("release", key))


def detected_hand(index=FingerPosition.STRAIGHT, palm=PalmPosition.FACING_CAMERA):
    index_scores = {"straight": 8.0, "partial": 30.0, "curled": 60.0, "closed": 95.0}
    scores = {
        "thumb": (12.0, FingerPosition.STRAIGHT),
        "index": (index_scores[index.value], index),
        "middle": (35.0, FingerPosition.PARTIAL),
        "ring": (60.0, FingerPosition.CURLED),
        "pinky": (100.0, FingerPosition.CLOSED),
    }
    return GestureState(palm, {
        name: FingerState(score, position, (0.4, 0.5, 0.0))
        for name, (score, position) in scores.items()
    })


def detection_result(*hands):
    """Use classified hand states as mock landmark data for the detector."""
    return SimpleNamespace(
        hand_landmarks=[state for _name, state in hands],
        handedness=[
            [SimpleNamespace(category_name=name)] for name, _state in hands
        ],
    )


class GestureReportingTests(unittest.TestCase):
    def setUp(self):
        self.clock = MockClock()
        self.enterContext(patch("time.monotonic", lambda: self.clock.now))
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.input = RecordingInput()
        self.overlay = Mock()
        self.overlay.handleDisplay.side_effect = lambda frame: frame
        self.first = GestureDefinition(
            "first", "First gesture",
            GestureMatch(None, {"index": frozenset(("straight",))}),
            CommandSequence((CommandStep("key_tap", "q"),)),
        )
        self.second = GestureDefinition(
            "second", "Second gesture",
            GestureMatch(None, {"index": frozenset(("partial",))}),
            CommandSequence((
                CommandStep("key_tap", "w"), CommandStep("key_tap", " "),
            )),
        )
        self.config = GestureConfig(
            (self.first, self.second),
            GestureMatch(None, {"index": frozenset(("closed",))}),
        )
        def recording_executor(**kwargs):
            return CommandExecutor(input_simulator=self.input, **kwargs)

        with patch.object(handler_module, "CommandExecutor", side_effect=recording_executor):
            self.handler = GestureHandler(self.overlay, self.config)
        self.addCleanup(self.handler.close)
        self.frame = SimpleNamespace(shape=(720, 1280, 3))
        self.camera = Mock(requested_index=0)
        self.camera.status.return_value = ("ready", 0, 0, None)
        self.camera.read.return_value = self.frame
        self.tracker = Mock()
        self.tracker.detect.return_value = detection_result()
        detector = Mock()
        detector.update.side_effect = lambda hand, _name: hand
        self.enterContext(patch.object(application_module, "cv2", Mock()))
        with patch.object(application_module, "Gui"):
            self.app = Application(
                self.camera, self.tracker, Mock(), Mock(), detector, self.handler,
                Mock(), self.overlay, SimpleNamespace(data=SettingsData()),
            )
        self.app.panels.main.build(
            self.root, on_restart=lambda: None, on_close=lambda: None,
        )
        self.app.panels.settings = Mock(tracking_preview_active=False)
        self.live = self.app.panels.main.widget.live_gestures
        self.cards = self.live.hand_panels
        self.root.update_idletasks()
        # Start just after the normal 100 ms UI refresh, the problematic window.
        self.tick()

    def tick(self, *hands, seconds=0.01):
        self.clock.advance(seconds)
        self.tracker.detect.return_value = detection_result(*hands)
        self.app._process_frame_work()
        self.root.update_idletasks()

    def assert_summary(self, hand, *, status="Detected", palm="Facing Camera",
                       gesture="First gesture", command="q"):
        card = self.cards[hand]
        self.assertEqual(card.detection.get(), status)
        self.assertEqual(card.palm.get(), palm)
        self.assertEqual(card.gesture.get(), gesture)
        self.assertEqual(card.command.get(), command)

    def assert_empty(self, hand):
        self.assert_summary(
            hand, status="Not detected", palm="—", gesture="—", command="—",
        )
        for row in self.cards[hand].deviations._rows.values():
            self.assertEqual(row["details"].get(), "—\n—")
            self.assertEqual(row["ratio"], 0.0)

    def test_brief_gesture_is_reported_before_periodic_refresh(self):
        self.tick(("Left", detected_hand()))
        self.assertIn(("press", "q"), self.input.events)
        self.assert_summary("Left")
        self.tick(("Left", detected_hand(FingerPosition.CURLED)))
        self.assert_summary("Left", gesture="—", command="—")

    def test_held_gesture_remains_visible_without_resending_input(self):
        for _ in range(25):
            self.tick(("Left", detected_hand()))
            self.assert_summary("Left")
        self.assertEqual(self.input.events.count(("press", "q")), 1)
        self.assertEqual(self.input.events.count(("release", "q")), 1)

    def test_both_hands_show_their_own_complete_data(self):
        left = detected_hand()
        right = detected_hand(FingerPosition.PARTIAL, PalmPosition.NOT_FACING_CAMERA)
        self.tick(("Right", right), ("Left", left))
        self.assert_summary("Left")
        self.assert_summary(
            "Right", palm="Not Facing Camera", gesture="Second gesture", command="w → Space",
        )
        for name, state in (("Left", left), ("Right", right)):
            for finger_name, finger in state.fingers.items():
                row = self.cards[name].deviations._rows[finger_name]
                self.assertEqual(
                    row["details"].get(),
                    f"{finger.deviation:.1f}°\n{finger.position.label}",
                )
                self.assertAlmostEqual(row["ratio"], min(finger.deviation / 75.0, 1.0))
                self.assertEqual(
                    str(row["label"].cget("foreground")),
                    gesture_classification_color("Light", finger.position.semantic_class),
                )

    def test_changed_gesture_reports_current_mapping_while_input_is_locked(self):
        self.tick(("Left", detected_hand()))
        self.tick(("Left", detected_hand(FingerPosition.PARTIAL)))
        self.assert_summary("Left", gesture="Second gesture", command="w → Space")
        self.assertEqual(self.input.events, [("press", "q")])

    def test_missing_hand_clears_only_that_card_immediately(self):
        right = detected_hand(FingerPosition.PARTIAL)
        self.tick(("Left", detected_hand()), ("Right", right))
        self.tick(("Right", right))
        self.assert_empty("Left")
        self.assert_summary("Right", gesture="Second gesture", command="w → Space")

    def test_camera_unavailable_clears_previous_hand(self):
        self.tick(("Left", detected_hand()), seconds=0.11)
        self.assert_summary("Left")
        self.camera.read.return_value = None
        self.tick()
        self.assert_empty("Left")
        self.assertIsNone(self.app.panels.main.preview_fingers)

    def test_pause_and_disabled_tracking_clear_cards(self):
        self.tick(("Left", detected_hand()))
        self.app.tracking_paused = True
        self.tick(("Left", detected_hand()))
        self.assert_empty("Left")
        self.assertEqual(self.live.tracking_status.get(), "Tracking paused")
        self.app.tracking_paused = False
        self.tick(("Left", detected_hand()))
        self.assert_summary("Left")
        self.app.track_hands = False
        self.tick(("Left", detected_hand()))
        self.assert_empty("Left")
        self.assertEqual(self.live.tracking_status.get(), "Tracking disabled")

    def test_preview_reports_gesture_without_sending_input(self):
        self.app._tracking_tab_active = False
        self.app.panels.settings.tracking_preview_active = True
        self.tick(("Left", detected_hand()))
        self.assert_summary("Left")
        self.assertEqual(self.input.events, [])
        self.assertFalse(self.handler._input_locked)

    def test_saved_name_and_command_changes_replace_old_reporting(self):
        self.tick(("Left", detected_hand()))
        renamed = replace(
            self.first, name="Renamed gesture",
            commands=CommandSequence((CommandStep("key_tap", "e"),)),
        )
        self.app.apply_gesture_config(replace(
            self.config, definitions=(renamed, self.second),
        ))
        self.tick(("Left", detected_hand()))
        self.assert_summary("Left", gesture="Renamed gesture", command="e")

    def test_reset_clears_match_and_allows_another_input(self):
        self.tick(("Left", detected_hand()))
        self.tick(("Left", detected_hand(FingerPosition.CLOSED)))
        self.assert_summary("Left", gesture="—", command="—")
        self.assertFalse(self.handler._input_locked)
        self.tick(("Left", detected_hand()))
        self.assert_summary("Left")
        self.assertEqual(self.input.events.count(("press", "q")), 2)

    def test_unchanged_match_keeps_deviation_redraw_throttled(self):
        self.tick(("Left", detected_hand()), seconds=0.11)
        with patch.object(
            self.app.panels.main, "update_gesture_display",
            wraps=self.app.panels.main.update_gesture_display,
        ) as refresh:
            for _ in range(4):
                self.tick(("Left", detected_hand()))
                self.assert_summary("Left")
            refresh.assert_not_called()
            self.tick(("Left", detected_hand()), seconds=0.11)
            refresh.assert_called_once()


class TrackerPollingTests(unittest.TestCase):
    def setUp(self):
        self.landmarker = Mock()
        self.enterContext(patch.object(tracker_module, "mp", SimpleNamespace(
            Image=lambda **kwargs: kwargs,
            ImageFormat=SimpleNamespace(SRGB="rgb"),
            tasks=SimpleNamespace(
                BaseOptions=lambda **kwargs: kwargs,
                vision=SimpleNamespace(
                    HandLandmarkerOptions=lambda **kwargs: kwargs,
                    RunningMode=SimpleNamespace(LIVE_STREAM="live"),
                    HandLandmarker=SimpleNamespace(
                        create_from_options=lambda _options: self.landmarker,
                    ),
                ),
            ),
        )))
        self.enterContext(patch.object(tracker_module, "cv2", SimpleNamespace(
            COLOR_BGR2RGB=0, cvtColor=lambda frame, _format: frame,
        )))
        self.tracker = HandTracker()
        self.addCleanup(self.tracker.close)
        self.frame = SimpleNamespace(shape=(720, 1280, 3))

    def test_pending_inference_does_not_erase_last_received_result(self):
        result = detection_result(("Left", detected_hand()))
        self.tracker._on_result(result, None, 1)
        for _ in range(5):
            self.assertIs(self.tracker.detect(self.frame), result)
        self.assertEqual(self.landmarker.detect_async.call_count, 5)

    def test_new_result_replaces_previous_hand_and_empty_result_clears_it(self):
        left = detection_result(("Left", detected_hand()))
        right = detection_result(("Right", detected_hand(FingerPosition.PARTIAL)))
        empty = detection_result()
        for index, result in enumerate((left, right, empty), start=1):
            self.tracker._on_result(result, None, index)
            self.assertIs(self.tracker.detect(self.frame), result)


if __name__ == "__main__":
    unittest.main()
