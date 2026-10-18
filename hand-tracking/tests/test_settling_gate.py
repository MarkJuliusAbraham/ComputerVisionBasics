"""Motion-aware activation using fresh bend measurements and synthetic time."""

import unittest
from dataclasses import replace
from types import SimpleNamespace as Record
from unittest.mock import Mock, patch

from hand_tracking.backend.gestures.settling_gate import FingerSettlingGate
from hand_tracking.backend.gestures.finger_classifier import FingerState, FingerPosition
from hand_tracking.backend.gestures.gesture_config import GestureMatch
from hand_tracking.backend.gestures.gesture_config import (
    GestureConfig, GestureDefinition, CommandSequence, CommandStep,
)
from hand_tracking.backend.gestures.gesture_handler import GestureHandler
from hand_tracking.backend.settings.settings_manager import SettingsData, HAND_SETTINGS_SCOPE


def definition(name, **fingers):
    return Record(id=name, match=GestureMatch(None, {
        finger: frozenset({category}) for finger, category in fingers.items()}))


def state(index=0, pinky=0, index_category=FingerPosition.STRAIGHT,
          pinky_category=FingerPosition.STRAIGHT, wrist=0):
    return Record(palm=Record(value="front"), wrist=(wrist, 0, 0), fingers={
        "index": FingerState(index, index_category, (wrist, 0, 0)),
        "pinky": FingerState(pinky, pinky_category, (wrist, 0, 0)),
    })


class SettlingGateTests(unittest.TestCase):
    def setUp(self):
        self.gate = FingerSettlingGate()
        self.gate.configure(True, 90)
        self.a = definition("a", index="straight")
        self.b = definition("b", index="closed")

    def sample(self, now, pose, candidate=None, definitions=None, hand="Left"):
        return self.gate.allows(pose, hand, candidate, definitions or (self.a, self.b), now)

    def test_intermediate_candidate_is_replaced_then_final_pose_activates(self):
        self.assertFalse(self.sample(0, state(0), self.a))
        self.assertFalse(self.sample(.02, state(10), self.a))
        self.assertFalse(self.sample(.04, state(80, index_category=FingerPosition.CLOSED), self.b))
        self.assertTrue(self.sample(.06, state(81, index_category=FingerPosition.CLOSED), self.b))

    def test_cached_inference_does_not_make_moving_pose_settled(self):
        self.sample(0, state(0), self.a)
        self.assertFalse(self.sample(.02, state(10), self.a))
        for _ in range(20):
            self.assertFalse(self.sample(.02, state(10), self.a))
        self.assertTrue(self.sample(.04, state(10), self.a))

    def test_unrelated_finger_and_wrist_motion_do_not_block(self):
        self.sample(0, state(), self.a)
        self.assertTrue(self.sample(.02, state(pinky=90, wrist=10), self.a))

    def test_single_finger_distinguishing_competitor_is_watched(self):
        other = definition("other", index="straight", pinky="closed")
        definitions = (self.a, other)
        self.sample(0, state(), self.a, definitions)
        self.assertFalse(self.sample(.02, state(pinky=30), self.a, definitions))
        self.assertTrue(self.sample(.04, state(pinky=30), self.a, definitions))

    def test_nonmatching_frames_still_supply_motion_history(self):
        self.sample(0, state())
        self.assertTrue(self.sample(.02, state(1), self.a))

    def test_hand_loss_gap_reset_and_new_hand_require_fresh_pair(self):
        self.sample(0, state(), self.a)
        self.assertTrue(self.sample(.02, state(), self.a))
        self.assertFalse(self.sample(.02, state(), self.a, hand="Right"))
        self.gate.finish_frame(set())
        self.assertFalse(self.sample(.04, state(), self.a))
        self.assertTrue(self.sample(.06, state(), self.a))
        self.assertFalse(self.sample(1, state(), self.a))
        self.gate.reset()
        self.assertFalse(self.sample(1.02, state(), self.a))

    def test_disabled_bypasses_without_history(self):
        self.gate.configure(False, 90)
        self.assertTrue(self.sample(0, state(), self.a))

    def test_zero_speed_requires_identical_angles(self):
        self.gate.configure(True, 0)
        self.sample(0, state(), self.a)
        self.assertFalse(self.sample(.02, state(.01), self.a))
        self.assertTrue(self.sample(.04, state(.01), self.a))

    def test_settings_round_trip_and_validation(self):
        chosen = replace(SettingsData(), finger_settling_enabled=True, finger_settling_max_speed=120)
        self.assertEqual(SettingsData.from_dict(chosen.to_dict()), chosen)
        for value in (-1, float("nan"), float("inf"), "bad", True, 10001):
            self.assertTrue(HAND_SETTINGS_SCOPE.validation_error(
                replace(chosen, finger_settling_max_speed=value)))
            self.assertEqual(SettingsData.from_dict({"finger_settling_max_speed": value})
                             .finger_settling_max_speed, 90)


class SettlingHandlerTests(unittest.TestCase):
    def setUp(self):
        definitions = tuple(GestureDefinition(
            id=key, name=key, match=GestureMatch(None, {"index": frozenset({category})}),
            commands=CommandSequence((CommandStep("key_tap", key),)),
            use_optimistic_tracking=False,
        ) for key, category in (("a", "straight"), ("b", "curled")))
        config = GestureConfig(definitions, GestureMatch(None, {"index": frozenset({"closed"})}))
        self.executor = Mock()
        with patch("hand_tracking.backend.gestures.gesture_handler.CommandExecutor",
                   return_value=self.executor):
            self.handler = GestureHandler(config, wrist_history=Mock())
        self.handler.configure_settling(replace(SettingsData(), finger_settling_enabled=True))

    def sample(self, now, angle, category=FingerPosition.STRAIGHT, **kwargs):
        pose = state(angle, index_category=category)
        pose.palm_size = .2
        return self.handler.handle(pose, "Left", sample_time=now, **kwargs)

    def test_only_settled_final_candidate_executes_and_latch_prevents_duplicates(self):
        self.assertEqual(self.sample(0, 0).id, "a")
        self.sample(.02, 10)
        self.sample(.04, 60, FingerPosition.CURLED)
        self.sample(.04, 60, FingerPosition.CURLED)
        self.executor.execute.assert_not_called()
        self.assertEqual(self.sample(.06, 61, FingerPosition.CURLED).id, "b")
        self.assertEqual(self.executor.execute.call_args.args[0].steps[0].value, "b")
        self.sample(.08, 61, FingerPosition.CURLED)
        self.assertEqual(self.executor.execute.call_count, 1)

    def test_preview_never_fires_and_suspend_discards_candidate_history(self):
        self.sample(0, 0, invoke_commands=False)
        self.sample(.02, 0, invoke_commands=False)
        self.executor.execute.assert_not_called()
        self.sample(.04, 0)
        self.handler.suspend()
        self.sample(.06, 0)
        self.executor.execute.assert_not_called()
        self.sample(.08, 0)
        self.executor.execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
