"""State and validation model for editable gesture mappings.

This module deliberately knows nothing about Dear PyGui.  The control window
only translates widget values into this model and renders the resulting state.
"""

from copy import deepcopy
from dataclasses import replace

from gestures.gesture_config import (
    CommandSequence, CommandStep, GestureConfig, GestureMatch, RepeatSettings,
)


class MappingModel:
    """Own the draft, baseline, and serialization state for one profile."""

    def __init__(self, config):
        self.load(config)

    @staticmethod
    def draft_from_definition(definition):
        return {
            "name": definition.name,
            "palm": definition.match.palm,
            "fingers": {name: set(values) for name, values in definition.match.fingers.items()},
            "commands": ", ".join(step.value for step in definition.commands.steps),
            "delay": definition.commands.delay_ms_between_steps,
            "tracked_finger": definition.tracked_finger,
        }

    def load(self, config):
        self.config = config
        self.definitions = list(config.definitions)
        self.drafts = {item.id: self.draft_from_definition(item) for item in self.definitions}
        self.baseline_drafts = deepcopy(self.drafts)
        self.baseline_definitions = list(self.definitions)
        self.reset_palm = config.reset_match.palm
        self.reset_fingers = {
            name: set(values) for name, values in config.reset_match.fingers.items()
        }
        repeat = config.repeat_settings
        self.repeat_values = {
            "initial_displacement": repeat.initial_displacement,
            "distance_threshold": repeat.distance_threshold,
            "min_interval_ms": repeat.min_interval_seconds * 1000,
            "max_repeats": repeat.max_repeats,
        }
        self.baseline_reset = (self.reset_palm, deepcopy(self.reset_fingers))
        self.baseline_repeat = dict(self.repeat_values)

    def is_dirty(self):
        return (
            self.drafts != self.baseline_drafts
            or self.definitions != self.baseline_definitions
            or self.repeat_values != self.baseline_repeat
            or (self.reset_palm, self.reset_fingers) != self.baseline_reset
        )

    def build_config(self):
        definitions = []
        for base in self.definitions:
            draft = self.drafts[base.id]
            command_values = [item.strip() for item in draft["commands"].split(",")]
            if not command_values or any(len(item) != 1 for item in command_values):
                raise ValueError(
                    f"{draft['name']}: enter one key per command step, separated by commas."
                )
            fingers = {
                name: frozenset(positions)
                for name, positions in draft["fingers"].items() if positions
            }
            match = GestureMatch(draft["palm"], fingers)
            sequence = CommandSequence(
                tuple(CommandStep("key_tap", item) for item in command_values),
                int(draft["delay"]),
            )
            definitions.append(replace(
                base, name=draft["name"], match=match,
                commands=sequence, tracked_finger=draft["tracked_finger"],
            ))

        repeat = RepeatSettings.from_dict({
            "initial_displacement": float(self.repeat_values["initial_displacement"]),
            "distance_threshold": float(self.repeat_values["distance_threshold"]),
            "min_interval_seconds": float(self.repeat_values["min_interval_ms"]) / 1000,
            "max_repeats": int(self.repeat_values["max_repeats"]),
        })
        reset = GestureMatch(
            self.reset_palm,
            {name: frozenset(values) for name, values in self.reset_fingers.items() if values},
        )
        if reset.palm is None and not reset.fingers:
            raise ValueError("Reset gesture must constrain palm orientation or at least one finger.")
        config = replace(
            self.config, definitions=tuple(definitions),
            repeat_settings=repeat, reset_match=reset,
        )
        GestureConfig._validate_no_overlaps(config.definitions)
        return config

    def commit(self, config):
        self.load(config)
