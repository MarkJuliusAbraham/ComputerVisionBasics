"""Wrist motion qualification for optimistic tracking, with synthetic paths."""

import random
import unittest
from dataclasses import asdict, replace

from hand_tracking.backend.gestures.optimistic.history import WristMovementHistory
from hand_tracking.backend.gestures.optimistic.settings import OptimisticTrackingSettings
from hand_tracking.backend.gestures.optimistic.smoothing import OneEuroFilter

DETECTION_RATE_HZ = 30
HAND = "Right"


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def settings(**changes) -> OptimisticTrackingSettings:
    """Wide lookback so every test path stays inside the window."""
    return replace(OptimisticTrackingSettings(), lookback_seconds=3.0, **changes)


def record_path(history, clock, points, palm_size=None, repeats=1) -> None:
    """Feed one detection per point; ``repeats`` mimics cached results seen again."""
    for point in points:
        clock.now += 1 / DETECTION_RATE_HZ
        for _ in range(repeats):
            history.record(HAND, point, palm_size)


def straight_move(start, distance, frames):
    x, y = start
    return [(x + distance * step / frames, y, 0.0) for step in range(1, frames + 1)]


def jitter_at(point, frames, spread, seed=7):
    noise = random.Random(seed)
    x, y = point
    return [(x + noise.gauss(0, spread), y + noise.gauss(0, spread), 0.0) for _ in range(frames)]


class OneEuroFilterTests(unittest.TestCase):
    def test_reduces_jitter_at_rest_and_follows_movement(self) -> None:
        smoother = OneEuroFilter(min_cutoff_hz=1.0, beta=5.0)
        noisy = jitter_at((0.5, 0.5), 90, spread=0.004)
        outputs = [smoother(frame / DETECTION_RATE_HZ, point) for frame, point in enumerate(noisy)]
        raw_steps = sum(abs(b[0] - a[0]) for a, b in zip(noisy, noisy[1:]))
        smooth_steps = sum(abs(b[0] - a[0]) for a, b in zip(outputs, outputs[1:]))
        self.assertLess(smooth_steps, raw_steps / 4)

        smoother.reset()
        moved = [smoother(frame / DETECTION_RATE_HZ, (0.1 + 0.01 * frame,)) for frame in range(31)]
        self.assertAlmostEqual(moved[-1][0], 0.4, delta=0.03)


class WristQualificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()

    def history(self, **changes) -> WristMovementHistory:
        return WristMovementHistory(settings(**changes), clock=self.clock)

    def test_jitter_after_a_small_move_does_not_qualify(self) -> None:
        # A small real move crosses the starting buffer; resting jitter must
        # not then add up to the activation distance.
        history = self.history()
        record_path(history, self.clock, straight_move((0.5, 0.5), 0.04, 9))
        record_path(history, self.clock, jitter_at((0.54, 0.5), 45, spread=0.004))
        self.assertIsNone(history.modifier_for(HAND))

    def test_deliberate_movement_qualifies(self) -> None:
        history = self.history()
        record_path(history, self.clock, straight_move((0.3, 0.5), 0.2, 12))
        self.assertIsNotNone(history.modifier_for(HAND))

    def test_repeated_cached_detections_count_once(self) -> None:
        once, repeated = self.history(), self.history()
        record_path(once, self.clock, straight_move((0.3, 0.5), 0.13, 12))
        self.clock.now = 100.0
        record_path(repeated, self.clock, straight_move((0.3, 0.5), 0.13, 12), repeats=20)
        self.assertEqual(
            [sample.point for sample in once._hands[HAND].samples],
            [sample.point for sample in repeated._hands[HAND].samples],
        )

    def test_hand_size_scaling_counts_the_same_motion_at_any_distance(self) -> None:
        # The same motion, 1.2 palm lengths, seen near and far from the camera.
        near_palm, far_palm = 0.26, 0.065
        for scaled, far_qualifies in ((False, False), (True, True)):
            with self.subTest(scale_with_hand_size=scaled):
                results = []
                for palm in (near_palm, far_palm):
                    history = self.history(smoothing_min_cutoff_hz=0.0, scale_with_hand_size=scaled)
                    record_path(history, self.clock, straight_move((0.2, 0.5), 1.2 * palm, 12), palm)
                    results.append(history.modifier_for(HAND) is not None)
                self.assertEqual(results, [True, far_qualifies])

    def test_missing_palm_size_stops_scaled_tracking(self) -> None:
        history = self.history(scale_with_hand_size=True)
        record_path(history, self.clock, straight_move((0.3, 0.5), 0.3, 12), palm_size=None)
        self.assertIsNone(history.modifier_for(HAND))


class SettingsTests(unittest.TestCase):
    def test_older_saved_settings_load_with_new_defaults(self) -> None:
        loaded = OptimisticTrackingSettings.from_dict({"enabled": True, "lookback_seconds": 2.0})
        defaults = OptimisticTrackingSettings()
        self.assertEqual(loaded.smoothing_min_cutoff_hz, defaults.smoothing_min_cutoff_hz)
        self.assertEqual(loaded.smoothing_beta, defaults.smoothing_beta)
        self.assertFalse(loaded.scale_with_hand_size)

    def test_new_fields_survive_saving(self) -> None:
        original = settings(
            smoothing_min_cutoff_hz=2.5, smoothing_beta=0.5,
            scale_with_hand_size=True, reference_palm_size=0.2,
        )
        self.assertEqual(OptimisticTrackingSettings.from_dict(asdict(original)), original)

    def test_rejects_invalid_values(self) -> None:
        for changes in (
            {"reference_palm_size": 0.0},
            {"smoothing_beta": -1.0},
            {"scale_with_hand_size": "yes"},
        ):
            with self.subTest(**changes), self.assertRaises(ValueError):
                settings(**changes)


if __name__ == "__main__":
    unittest.main()
