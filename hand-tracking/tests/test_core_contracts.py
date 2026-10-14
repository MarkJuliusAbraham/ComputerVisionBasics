"""Durable behavior checks, independent of the UI and tracking hardware."""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from hand_tracking.gestures.gesture_config import (
    CommandSequence,
    CommandStep,
    GestureConfig,
    GestureDefinition,
    GestureMatch,
)
from hand_tracking.gestures.tracking.settings import GestureTrackingSettings
from hand_tracking.input.command_executor import CommandExecutor
from hand_tracking.input.command_modifier import CommandModifier
from hand_tracking.settings.settings_manager import Settings, SettingsData


class RecordingInput:
    """Record requested key events without sending anything to the OS."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def press(self, key: str) -> None:
        self.events.append(("press", key))

    def release(self, key: str) -> None:
        self.events.append(("release", key))


def sample_profile() -> GestureConfig:
    """Use synthetic data so shipped profiles and user preferences can change."""
    gesture = GestureDefinition(
        id="test_gesture",
        name="Test gesture",
        match=GestureMatch(None, {"index": frozenset({"straight"})}),
        commands=CommandSequence(
            (CommandStep("key_tap", "a"), CommandStep("key_tap", "b")),
            delay_ms_between_steps=125,
        ),
        tracking=GestureTrackingSettings(fingers=("index", "middle")),
        use_optimistic_tracking=False,
    )
    return GestureConfig(
        definitions=(gesture,),
        reset_match=GestureMatch(None, {"index": frozenset({"closed"})}),
    )


class CoreContractTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def test_saved_settings_survive_reload(self) -> None:
        path = str(self.directory / "settings.json")
        settings = Settings(path)
        chosen = replace(SettingsData(), theme="Dark", ui_scale="150%", profile=False)

        settings.update(chosen)

        self.assertEqual(Settings(path).data, chosen)

    def test_saved_profile_preserves_gestures_and_commands(self) -> None:
        path = self.directory / "profile.json"
        profile = sample_profile()

        profile.save(path)

        self.assertEqual(GestureConfig.load(path), profile)

    def test_invalid_profile_cannot_replace_a_saved_profile(self) -> None:
        path = self.directory / "profile.json"
        profile = sample_profile()
        profile.save(path)
        saved_bytes = path.read_bytes()
        gesture = profile.definitions[0]
        duplicate = replace(gesture, name="Duplicate identity")
        invalid = replace(profile, definitions=(gesture, duplicate))

        with self.assertRaises(ValueError):
            invalid.save(path)

        self.assertEqual(path.read_bytes(), saved_bytes)
        self.assertEqual(GestureConfig.load(path), profile)

    def test_cancelling_commands_releases_input_and_stops_pending_work(self) -> None:
        keyboard = RecordingInput()
        executor = CommandExecutor(input_simulator=keyboard)
        sequence = sample_profile().definitions[0].commands

        # Both submissions happen before any scheduled key release is due.
        with patch("hand_tracking.input.command_executor.time.monotonic", return_value=0.0):
            executor.execute(sequence, modifier=CommandModifier(repeat_count=2))
            executor.execute(sequence)
        self.assertEqual(keyboard.events, [("press", "a")])

        executor.clear()
        self.assertEqual(keyboard.events, [("press", "a"), ("release", "a")])

        # Advancing time must not revive queued steps, repeats, or sequences.
        for now in (1.0, 10.0, 1000.0):
            executor.update(now=now)
        executor.clear()
        self.assertEqual(keyboard.events, [("press", "a"), ("release", "a")])


if __name__ == "__main__":
    unittest.main()
