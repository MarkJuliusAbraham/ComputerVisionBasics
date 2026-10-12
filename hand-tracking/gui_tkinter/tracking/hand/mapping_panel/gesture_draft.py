"""Portable editing data for a gesture's criteria and command sequence."""

from dataclasses import dataclass, replace

from gestures.gesture_config import (
    CommandSequence,
    CommandStep,
    GestureDefinition,
    GestureMatch,
)


@dataclass(frozen=True)
class GestureDraft:
    """Keep unfinished command text separate from a validated definition."""

    criteria: GestureMatch
    commands: str
    delay: str

    @classmethod
    def from_definition(cls, definition: GestureDefinition):
        return cls(
            criteria=definition.match,
            commands=", ".join(step.value for step in definition.commands.steps),
            delay=str(definition.commands.delay_ms_between_steps),
        )

    def to_definition(self, definition: GestureDefinition):
        command_values = [value.strip() for value in self.commands.split(",")]
        if any(len(value) != 1 for value in command_values):
            raise ValueError(
                f"{definition.name}: enter one character for each command step"
            )
        try:
            delay = int(self.delay)
        except (TypeError, ValueError) as error:
            raise ValueError("Delay must be a whole number of milliseconds") from error
        if delay < 0:
            raise ValueError("Delay cannot be negative")

        sequence = CommandSequence(
            steps=tuple(CommandStep(type="key_tap", value=value) for value in command_values),
            delay_ms_between_steps=delay,
        )
        # Replacing only editable fields retains tracking and repeat metadata.
        return replace(definition, match=self.criteria, commands=sequence)
