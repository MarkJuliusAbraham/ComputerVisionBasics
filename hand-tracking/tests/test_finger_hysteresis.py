"""Finger category stability without camera, models, or gesture definitions."""

import unittest
from dataclasses import replace

from hand_tracking.backend.gestures.finger_classifier import FingerClassifier, FingerState
from hand_tracking.backend.gestures.finger_hysteresis import FingerHysteresis
from hand_tracking.backend.gestures.finger_thresholds import FingerThresholds
from hand_tracking.backend.settings.settings_manager import SettingsData, HAND_SETTINGS_SCOPE


class FingerHysteresisTests(unittest.TestCase):
    def setUp(self):
        self.thresholds = FingerThresholds.defaults()
        self.layer = FingerHysteresis(self.thresholds.splits, self.thresholds.categories, 3)

    def sample(self, angle, hand="Left", finger="index", layer=None, thresholds=None):
        thresholds = thresholds or self.thresholds
        state = FingerState(angle, thresholds.classify(angle), (1, 2, 3))
        return (layer or self.layer).apply(hand, {finger: state})[finger]

    def test_jitter_holds_category_until_directional_boundary_is_crossed(self):
        straight, partial = self.thresholds.categories[:2]
        self.assertEqual(self.sample(14).position, straight)
        for angle in (15, 17, 14, 18):
            self.assertEqual(self.sample(angle).position, straight)
        self.assertEqual(self.sample(18.1).position, partial)
        for angle in (16, 14, 12):
            self.assertEqual(self.sample(angle).position, partial)
        self.assertEqual(self.sample(11.9).position, straight)

    def test_each_hand_and_finger_has_independent_memory(self):
        self.sample(14)
        partial = self.thresholds.categories[1]
        self.assertEqual(self.sample(16, hand="Right").position, partial)
        self.assertEqual(self.sample(16, finger="middle").position, partial)
        self.assertEqual(self.sample(16).position, self.thresholds.categories[0])

    def test_large_movements_skip_bands_for_all_supported_segment_counts(self):
        for count in (4, 5, 6):
            thresholds = FingerThresholds.defaults(count)
            layer = FingerHysteresis(thresholds.splits, thresholds.categories, 3)
            self.sample(0, layer=layer, thresholds=thresholds)
            self.assertEqual(self.sample(120, layer=layer, thresholds=thresholds).position,
                             thresholds.categories[-1])
            self.assertEqual(self.sample(0, layer=layer, thresholds=thresholds).position,
                             thresholds.categories[0])

    def test_zero_margin_exactly_preserves_stateless_classification(self):
        layer = FingerHysteresis(self.thresholds.splits, self.thresholds.categories, 0)
        for angle in (14, 15, 15.1, 45, 75, 120, 0):
            self.assertEqual(self.sample(angle, layer=layer).position, self.thresholds.classify(angle))

    def test_loss_and_reset_discard_memory_without_affecting_present_hand(self):
        self.sample(14)
        self.sample(14, hand="Right")
        self.layer.finish_frame({"Right"})
        self.assertEqual(self.sample(16).position, self.thresholds.categories[1])
        self.assertEqual(self.sample(16, hand="Right").position, self.thresholds.categories[0])
        self.layer.reset()
        self.assertEqual(self.sample(16, hand="Right").position, self.thresholds.categories[1])

    def test_measured_angle_and_tip_are_preserved(self):
        self.sample(14)
        output = self.sample(17)
        self.assertEqual(output.deviation, 17)
        self.assertEqual(output.tip, (1, 2, 3))
        self.assertEqual(output.position, self.thresholds.categories[0])

    def test_settings_round_trip_and_invalid_values(self):
        chosen = replace(SettingsData(), finger_hysteresis_enabled=True,
                         finger_hysteresis_margin_degrees=4.5)
        self.assertEqual(SettingsData.from_dict(chosen.to_dict()), chosen)
        self.assertFalse(SettingsData.from_dict({}).finger_hysteresis_enabled)
        for value in (-1, 31, float("nan"), float("inf"), True, "bad"):
            self.assertTrue(HAND_SETTINGS_SCOPE.validation_error(
                replace(chosen, finger_hysteresis_margin_degrees=value)))
            self.assertEqual(SettingsData.from_dict({"finger_hysteresis_margin_degrees": value})
                             .finger_hysteresis_margin_degrees, 3)


if __name__ == "__main__":
    unittest.main()
