"""Simple path-distance repeats, independent of pose and hardware."""

from types import SimpleNamespace
import unittest

from hand_tracking.backend.gestures.repeating.controller import MovementRepeatController
from hand_tracking.backend.gestures.repeating.settings import MovementBufferSettings, RepeatSettings
from hand_tracking.backend.gestures.tracking.path import PathSegment
from hand_tracking.backend.gestures.tracking.settings import GestureTrackingSettings


class DistanceRepeatTests(unittest.TestCase):
    def setUp(self):
        self.repeats = []
        self.markers = []
        self.now = 0
        def repeat(definition, *, on_start):
            self.repeats.append(definition.id)
            on_start()
        self.controller = MovementRepeatController(
            repeat, lambda *args: self.markers.append(args), clock=lambda: self.now,
        )
        self.definition = SimpleNamespace(
            id="distance", tracking=GestureTrackingSettings(fingers=("index", "middle")),
            repeat_settings=RepeatSettings(
                trigger="distance", distance_threshold=0.1, max_repeats=4, min_interval_seconds=0,
                movement=MovementBufferSettings(initial_displacement=0.9),
            ),
        )
        self.controller.start(self.definition, SimpleNamespace(fingers={
            name: SimpleNamespace(tip=(0, 0, 0)) for name in ("index", "middle")
        }))

    def move(self, start, end, middle_start=None, middle_end=None):
        self.controller.observe({
            "index": PathSegment((start, 0, 0), (end, 0, 0)),
            "middle": PathSegment(
                (start if middle_start is None else middle_start, 0, 0),
                (end if middle_end is None else middle_end, 0, 0),
            ),
        })

    def test_threshold_and_remainder_without_starting_buffer(self):
        self.move(0, 0.125)
        self.assertEqual(len(self.repeats), 1)
        self.move(0.125, 0.19)
        self.assertEqual(len(self.repeats), 1)
        self.move(0.19, 0.21)
        self.assertEqual(len(self.repeats), 2)

    def test_return_motion_counts_as_travel(self):
        self.move(0, 0.06)
        self.move(0.06, 0)
        self.assertEqual(len(self.repeats), 1)

    def test_selected_fingers_are_averaged(self):
        self.move(0, 0.12, middle_start=0, middle_end=0)
        self.assertEqual(self.repeats, [])
        self.move(0.12, 0.22, middle_start=0, middle_end=0)
        self.assertEqual(len(self.repeats), 1)

    def test_one_frame_can_earn_multiple_repeats_up_to_limit(self):
        self.move(0, 0.55)
        for _ in range(6):
            self.controller.update()
        self.assertEqual(len(self.repeats), 4)
        self.assertEqual(len(self.markers), 8)

    def test_interrupt_preserves_remainder_without_counting_unseen_jump(self):
        self.move(0, 0.06)
        self.controller.interrupt_motion()
        self.assertTrue(self.controller.remembers_gesture)
        self.move(0.06, 0.8)
        self.assertEqual(self.repeats, [])
        self.move(0.8, 0.85)
        self.assertEqual(len(self.repeats), 1)

    def test_settings_round_trip(self):
        settings = self.definition.repeat_settings
        self.assertEqual(RepeatSettings.from_dict(settings.to_dict()), settings)
