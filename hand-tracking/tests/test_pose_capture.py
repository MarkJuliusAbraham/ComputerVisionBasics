"""Building gesture criteria from captured poses, with synthetic hand reports."""

import unittest

from hand_tracking.backend.gestures.detector import GestureState
from hand_tracking.backend.gestures.finger_classifier import FingerPosition, FingerState
from hand_tracking.backend.gestures.gesture_matcher import GestureMatcher
from hand_tracking.backend.gestures.hand_landmarks import FINGER_NAMES
from hand_tracking.backend.gestures.hand_report import HandReport
from hand_tracking.backend.gestures.palm_detector import PalmPosition
from hand_tracking.backend.gestures.pose_capture import PoseCapture

FACING = PalmPosition.FACING_CAMERA
AWAY = PalmPosition.NOT_FACING_CAMERA


def report(positions, palm=FACING, handedness="Right") -> HandReport:
    """A report whose unspecified fingers are closed."""
    fingers = {
        name: FingerState(0.0, positions.get(name, FingerPosition.CLOSED), (0.0, 0.0, 0.0))
        for name in FINGER_NAMES
    }
    return HandReport(handedness, GestureState(palm, fingers))


class PoseCaptureTests(unittest.TestCase):
    def test_captured_pose_matches_itself(self) -> None:
        pose = report({"index": FingerPosition.STRAIGHT, "middle": FingerPosition.CURLED})
        capture = PoseCapture()
        for _ in range(10):
            capture.add(pose)
        for allowance in (0, 1, 2):
            with self.subTest(allowance=allowance):
                match = capture.result(allowance)
                self.assertEqual(match.palm, FACING.value)
                self.assertTrue(GestureMatcher.matches(match, pose.state))

    def test_extreme_bands_gain_the_allowance_toward_the_middle(self) -> None:
        capture = PoseCapture(segment_count=4)
        capture.add(report({"index": FingerPosition.STRAIGHT}))  # Other fingers closed
        cases = {
            0: ({"straight"}, {"closed"}),
            1: ({"straight", "partial"}, {"curled", "closed"}),
            2: ({"straight", "partial", "curled"}, {"partial", "curled", "closed"}),
        }
        for allowance, (straight, closed) in cases.items():
            with self.subTest(allowance=allowance):
                match = capture.result(allowance)
                self.assertEqual(match.fingers["index"], frozenset(straight))
                self.assertEqual(match.fingers["ring"], frozenset(closed))

    def test_middle_bands_stay_exact(self) -> None:
        capture = PoseCapture(segment_count=4)
        capture.add(report({"index": FingerPosition.PARTIAL}))
        self.assertEqual(capture.result(2).fingers["index"], frozenset({"partial"}))

    def test_the_most_frequent_band_wins_over_brief_flicker(self) -> None:
        # A stray frame, such as a stale result or a moment near a threshold,
        # does not widen the rule.
        capture = PoseCapture(segment_count=4)
        for position in (FingerPosition.CURLED, *[FingerPosition.STRAIGHT] * 6):
            capture.add(report({"index": position}))
        self.assertEqual(capture.result(0).fingers["index"], frozenset({"straight"}))

    def test_inconsistent_palm_is_left_unrestricted(self) -> None:
        capture = PoseCapture()
        for palm in (FACING, AWAY, FACING, AWAY):
            capture.add(report({}, palm=palm))
        self.assertIsNone(capture.result().palm)

    def test_only_the_first_hand_seen_is_captured(self) -> None:
        capture = PoseCapture()
        self.assertTrue(capture.add(report({"index": FingerPosition.STRAIGHT}, handedness="Left")))
        self.assertFalse(capture.add(report({"index": FingerPosition.CLOSED}, handedness="Right")))
        self.assertEqual(capture.handedness, "Left")
        self.assertEqual(capture.result(0).fingers["index"], frozenset({"straight"}))

    def test_no_hand_gives_no_criteria(self) -> None:
        self.assertIsNone(PoseCapture().result())


if __name__ == "__main__":
    unittest.main()
