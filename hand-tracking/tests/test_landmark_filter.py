"""Coordinate-layer behavior with synthetic, timestamped detections."""

import math
import unittest
from dataclasses import replace
from types import SimpleNamespace as Record

from hand_tracking.backend.landmarker.landmark_filter import LandmarkFilter
from hand_tracking.backend.settings.settings_manager import SettingsData, HAND_SETTINGS_SCOPE


def detection(timestamp, x=None, name="Left"):
    return Record(timestamp_ms=timestamp,
                  hand_landmarks=[] if x is None else [[Record(x=x, y=x, z=x)]],
                  handedness=[] if x is None else [[Record(category_name=name)]])


class LandmarkFilterTests(unittest.TestCase):
    def test_bypass_is_exact_and_toggle_resets_history(self):
        layer = LandmarkFilter()
        raw = detection(0, 0)
        self.assertIs(layer.apply(raw), raw)
        layer.configure(True, 1, 0)
        layer.apply(raw)
        self.assertLess(layer.apply(detection(20, 1)).hand_landmarks[0][0].x, 1)
        layer.configure(False, 1, 0)
        self.assertIs(layer.apply(raw), raw)
        layer.configure(True, 1, 0)
        self.assertEqual(layer.apply(detection(40, 1)).hand_landmarks[0][0].x, 1)

    def test_low_pass_formula_cache_and_raw_data_preservation(self):
        layer = LandmarkFilter()
        layer.configure(True, 1, 0)
        layer.apply(detection(0, 0))
        raw = detection(20, 1)
        output = layer.apply(raw)
        self.assertAlmostEqual(output.hand_landmarks[0][0].x, 1 / (1 + 1 / (2 * math.pi * .02)))
        self.assertEqual(raw.hand_landmarks[0][0].x, 1)
        self.assertIs(layer.apply(raw), output)
        self.assertIs(layer.apply(detection(20, 99)), output)

    def test_speed_response_reduces_lag(self):
        outputs = []
        for beta in (0, 5):
            layer = LandmarkFilter()
            layer.configure(True, 1, beta)
            layer.apply(detection(0, 0))
            outputs.append(layer.apply(detection(20, 1)).hand_landmarks[0][0].x)
        self.assertGreater(outputs[1], outputs[0])

    def test_loss_long_gap_and_handedness_change_start_fresh(self):
        for next_sample in (detection(400, 1), detection(20, 1, "Right")):
            layer = LandmarkFilter()
            layer.configure(True, 1, 0)
            layer.apply(detection(0, 0))
            self.assertEqual(layer.apply(next_sample).hand_landmarks[0][0].x, 1)
        layer.apply(detection(420))
        self.assertEqual(layer.apply(detection(440, 2)).hand_landmarks[0][0].x, 2)

    def test_settings_round_trip_and_validation(self):
        chosen = replace(SettingsData(), one_euro_enabled=True, one_euro_min_cutoff_hz=.8, one_euro_beta=2)
        self.assertEqual(SettingsData.from_dict(chosen.to_dict()), chosen)
        self.assertFalse(SettingsData.from_dict({}).one_euro_enabled)
        for value in (0, -1, float("nan"), float("inf"), True, "bad"):
            self.assertTrue(HAND_SETTINGS_SCOPE.validation_error(replace(chosen, one_euro_min_cutoff_hz=value)))
            self.assertEqual(SettingsData.from_dict({"one_euro_min_cutoff_hz": value}).one_euro_min_cutoff_hz, 1)


if __name__ == "__main__":
    unittest.main()
