"""Synthetic wrist motion and repeat scheduling; no hardware or real keys."""

from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from hand_tracking.backend.gestures.gesture_config import (
    CommandSequence, CommandStep, GestureConfig, GestureDefinition, GestureMatch,
)
from hand_tracking.backend.gestures.gesture_handler import GestureHandler

from hand_tracking.backend.gestures.repeating.controller import MovementRepeatController
from hand_tracking.backend.gestures.repeating.settings import RepeatSettings
from hand_tracking.backend.gestures.repeating.shake import HandShakeDetector
from hand_tracking.backend.gestures.tracking.settings import GestureTrackingSettings
from hand_tracking.backend.gestures.tracking.path import PathSegment
from hand_tracking.frontend.components.movement_draft import MovementSettingsDraft


class ShakeTests(unittest.TestCase):
    def setUp(self):
        self.settings = RepeatSettings(trigger="shake", shake_amplitude=0.35)
        self.detector = HandShakeDetector(self.settings)

    def sample(self, x, now, y=0.5, size=0.2):
        return self.detector.observe((x, y, 0.0), size, now)

    def test_fingertips_can_shake_with_stationary_wrist(self):
        wrist = (0.5, 0.5, 0)
        def tips(offset):
            return {str(i): (0.5 + offset, 0.3, 0) for i in range(5)}
        self.assertFalse(self.detector.observe(wrist, 0.2, 0, tips(0)))
        self.assertFalse(self.detector.observe(wrist, 0.2, 0.1, tips(0.1)))
        self.assertTrue(self.detector.observe(wrist, 0.2, 0.2, tips(0)))

    def test_opposing_fingertip_motion_does_not_cancel(self):
        wrist = (0.5, 0.5, 0)
        def tips(offset):
            return {"index": (0.5 + offset, 0.3, 0), "middle": (0.5 - offset, 0.3, 0)}
        self.detector.observe(wrist, 0.2, 0, tips(0))
        self.assertFalse(self.detector.observe(wrist, 0.2, 0.1, tips(0.1)))
        self.assertTrue(self.detector.observe(wrist, 0.2, 0.2, tips(0)))

    def test_changed_landmark_group_rebases_motion(self):
        wrist = (0.5, 0.5, 0)
        self.detector.observe(wrist, 0.2, 0, {"index": (0.5, 0.3, 0)})
        self.detector.observe(wrist, 0.2, 0.1, {"index": (0.7, 0.3, 0)})
        self.assertFalse(self.detector.observe(wrist, 0.2, 0.2, {}))
        self.assertFalse(self.detector.observe(wrist, 0.2, 0.3, {"index": (0.5, 0.3, 0)}))

    def test_outgoing_stroke_does_not_repeat_but_return_does(self):
        self.assertFalse(self.sample(0.5, 0))
        self.assertFalse(self.sample(0.60, 0.1))
        self.assertTrue(self.sample(0.50, 0.2))
        self.assertFalse(self.sample(0.50, 0.21))
        self.assertFalse(self.sample(0.60, 0.3))
        self.assertTrue(self.sample(0.50, 0.4))

    def test_enough_travel_without_returning_near_origin_does_not_repeat(self):
        self.sample(0.5, 0)
        self.sample(0.6, 0.1)
        self.assertFalse(self.sample(0.55, 0.2))
        self.assertTrue(self.sample(0.51, 0.3))

    def test_returning_near_origin_without_enough_travel_does_not_repeat(self):
        self.sample(0.5, 0)
        self.sample(0.52, 0.1)
        self.assertFalse(self.sample(0.5, 0.2))

    def test_diagonal_motion_does_not_require_a_fixed_axis(self):
        self.sample(0.5, 0)
        self.sample(0.55, 0.1, y=0.55)
        self.assertTrue(self.sample(0.5, 0.2))

    def test_small_sustained_jitter_does_not_accumulate_into_a_shake(self):
        self.sample(0.5, 0)
        for index in range(1, 90):
            self.assertFalse(self.sample(0.51 if index % 2 else 0.49, index * 0.01))

    def test_jitter_and_one_way_motion_do_not_repeat(self):
        for index, x in enumerate((0.5, 0.51, 0.49, 0.51, 0.5)):
            self.assertFalse(self.sample(x, index * 0.05))
        for index in range(20):
            self.assertFalse(self.sample(0.5 + index * 0.02, 1 + index * 0.05))

    def test_slow_return_or_pause_does_not_repeat(self):
        self.sample(0.5, 0)
        self.sample(0.6, 0.1)
        self.assertFalse(self.sample(0.5, 1.0))

    def test_missing_or_invalid_sample_discards_stroke(self):
        for wrist, size in ((None, 0.2), ((float("nan"), 0, 0), 0.2), ((0.5, 0.5, 0), 0)):
            self.detector = HandShakeDetector(self.settings)
            self.sample(0.5, 0)
            self.sample(0.6, 0.1)
            self.assertFalse(self.detector.observe(wrist, size, 0.15))
            self.assertFalse(self.sample(0.5, 0.2))

    def test_hand_size_scaling_and_vertical_aspect(self):
        for size in (0.1, 0.3):
            self.detector = HandShakeDetector(self.settings, frame_aspect=0.5)
            self.sample(0.5, 0, size=size)
            self.sample(0.5, 0.1, y=0.5 + size, size=size)
            self.assertTrue(self.sample(0.5, 0.2, size=size))

    def test_settings_and_editable_draft_round_trip(self):
        self.assertEqual(RepeatSettings.from_dict({}).trigger, "tracking")
        custom = replace(self.settings, shake_amplitude=0.6, shake_window_seconds=0.7)
        self.assertEqual(RepeatSettings.from_dict(custom.to_dict()), custom)
        self.assertEqual(MovementSettingsDraft.from_settings(custom).to_settings(), custom)
        for changes in ({"trigger": "unknown"}, {"shake_amplitude": 0}, {"shake_window_seconds": float("nan")}):
            with self.assertRaises(ValueError):
                replace(custom, **changes)


class ShakeSchedulingTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.repeats = []
        def repeat(definition, *, on_start):
            self.repeats.append(definition.id)
            on_start()
        self.controller = MovementRepeatController(repeat, lambda *args: None, clock=lambda: self.now)
        self.definition = SimpleNamespace(
            id="shake", tracking=GestureTrackingSettings(),
            repeat_settings=RepeatSettings(trigger="shake", max_repeats=2, min_interval_seconds=0.3),
        )
        self.controller.start(self.definition, self.state(0.5))

    @staticmethod
    def state(x):
        return SimpleNamespace(wrist=(x, 0.5, 0), palm_size=0.2, fingers={})

    def observe(self, x, now):
        self.now = now
        self.controller.observe({}, self.state(x))

    def test_without_selected_fingers_respects_delay_and_budget(self):
        self.observe(0.6, 0.1)
        self.observe(0.5, 0.2)
        self.assertEqual(self.repeats, [])
        self.now = 0.31
        self.controller.update()
        self.assertEqual(self.repeats, ["shake"])
        self.observe(0.6, 0.32)
        self.observe(0.5, 0.4)
        self.now = 0.62
        self.controller.update()
        self.assertEqual(self.repeats, ["shake", "shake"])

    def test_clear_cancels_pending_repeat(self):
        self.observe(0.6, 0.1)
        self.observe(0.5, 0.2)
        self.controller.clear()
        self.now = 1
        self.controller.update()
        self.assertEqual(self.repeats, [])

    def test_controller_uses_all_fingertips_without_tracking_selection(self):
        def state(offset):
            return SimpleNamespace(
                wrist=(0.5, 0.5, 0), palm_size=0.2,
                fingers={str(i): SimpleNamespace(tip=(0.5 + offset, 0.3, 0)) for i in range(5)},
            )
        self.controller.start(self.definition, state(0))
        self.now = 0.1
        self.controller.observe({}, state(0.1))
        self.now = 0.2
        self.controller.observe({}, state(0))
        self.now = 0.31
        self.controller.update()
        self.assertEqual(self.repeats, ["shake"])

    def test_tracking_mode_still_repeats_on_distance_without_reversal(self):
        definition = SimpleNamespace(
            id="tracking", tracking=GestureTrackingSettings(fingers=("index",)),
            repeat_settings=RepeatSettings(min_interval_seconds=0),
        )
        state = SimpleNamespace(fingers={"index": SimpleNamespace(tip=(0.5, 0.5, 0))})
        self.controller.start(definition, state)
        self.controller.observe({"index": PathSegment((0.5, 0.5, 0), (0.8, 0.5, 0))})
        self.controller.update()
        self.assertEqual(self.repeats, ["tracking", "tracking"])


class RememberedShakeTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.commands = []
        self.executor = Mock()
        def execute(sequence, **kwargs):
            self.commands.append(sequence.steps[0].value)
            if kwargs.get("on_start"):
                kwargs["on_start"]()
        self.executor.execute.side_effect = execute
        settings = RepeatSettings(trigger="shake", min_interval_seconds=0, max_repeats=3)
        definitions = tuple(
            GestureDefinition(
                id=key, name=key,
                match=GestureMatch(None, {"index": frozenset({pose})}),
                commands=CommandSequence((CommandStep("key_tap", key),)),
                repeat_settings=settings,
            )
            for key, pose in (("a", "straight"), ("b", "curled"))
        )
        config = GestureConfig(
            definitions, GestureMatch(None, {"index": frozenset({"closed"})}),
        )
        with patch(
            "hand_tracking.backend.gestures.gesture_handler.CommandExecutor",
            return_value=self.executor,
        ):
            self.handler = GestureHandler(config, wrist_history=Mock())
        self.handler.repeat_controller = MovementRepeatController(
            self.handler._press, lambda *args: None, clock=lambda: self.now,
        )

    def pose(self, pose, x, now, hand="Left"):
        self.now = now
        state = SimpleNamespace(
            fingers={"index": SimpleNamespace(position=SimpleNamespace(value=pose), tip=(x, 0.5, 0))},
            wrist=(x, 0.5, 0), palm_size=0.2,
        )
        return self.handler.handle(state, hand)

    def test_pose_loss_or_another_match_still_repeats_last_triggered_gesture(self):
        self.pose("straight", 0.5, 0)
        self.pose("partial", 0.6, 0.1)
        matched = self.pose("curled", 0.5, 0.2)
        self.assertEqual(matched.id, "b")  # Live classification remains accurate.
        self.assertEqual(self.commands, ["a", "a"])
        self.handler.wrist_history.modifier_for.assert_not_called()

    def test_other_hand_cannot_repeat_remembered_gesture(self):
        self.pose("straight", 0.5, 0)
        self.pose("partial", 0.6, 0.1, hand="Right")
        self.pose("partial", 0.5, 0.2, hand="Right")
        self.assertEqual(self.commands, ["a"])

    def test_distance_mode_remembers_gesture_after_pose_changes(self):
        config = self.handler.config
        definitions = tuple(replace(
            definition, tracking=GestureTrackingSettings(fingers=("index",)),
            repeat_settings=replace(
                definition.repeat_settings, trigger="distance", distance_threshold=0.09,
            ),
        ) for definition in config.definitions)
        self.handler.configure(replace(config, definitions=definitions))
        self.pose("straight", 0.5, 0)
        self.pose("partial", 0.6, 0.1)
        self.pose("curled", 0.5, 0.2)
        self.assertEqual(self.commands, ["a", "a", "a"])
        self.handler.wrist_history.modifier_for.assert_not_called()

    def test_pause_and_hand_loss_retain_memory_but_discard_partial_shakes(self):
        for interrupt in (self.handler.suspend, lambda: self.handler.finish_frame(set())):
            self.handler.configure(self.handler.config)
            self.commands.clear()
            self.pose("straight", 0.5, 0)
            self.pose("partial", 0.6, 0.1)
            interrupt()
            self.assertTrue(self.handler.repeat_controller.remembers_shake_gesture)
            self.pose("partial", 0.5, 0.2)  # Must not complete the interrupted stroke.
            self.assertEqual(self.commands, ["a"])
            self.pose("partial", 0.6, 0.3)
            self.pose("partial", 0.5, 0.4)
            self.assertEqual(self.commands, ["a", "a"])

    def test_explicit_reset_forgets_gesture_and_allows_new_gesture(self):
        self.pose("straight", 0.5, 0)
        self.pose("closed", 0.6, 0.1)
        self.assertFalse(self.handler.repeat_controller.remembers_shake_gesture)
        self.pose("partial", 0.5, 0.2)
        self.assertEqual(self.commands, ["a"])
        self.pose("curled", 0.5, 0.3)
        self.pose("partial", 0.6, 0.4)
        self.pose("partial", 0.5, 0.5)
        self.assertEqual(self.commands, ["a", "b", "b"])

    def test_pausing_does_not_replenish_repeat_budget(self):
        self.pose("straight", 0.5, 0)
        for index in range(1, 8):
            self.pose("partial", 0.6 if index % 2 else 0.5, index * 0.04)
        self.assertEqual(len(self.commands), 4)  # Initial command plus three repeats.
        self.handler.suspend()
        for index in range(8, 14):
            self.pose("partial", 0.6 if index % 2 else 0.5, index * 0.04)
        self.assertEqual(len(self.commands), 4)
