"""Portable editing data for a gesture's criteria, tracking, commands, and repeats."""

from dataclasses import dataclass, replace

from gestures.gesture_config import (
    CommandSequence,
    CommandStep,
    GestureDefinition,
    GestureMatch,
)
from gestures.tracking.settings import GestureTrackingSettings

from gui_tkinter.components.movement_draft import MovementSettingsDraft


@dataclass(frozen=True)
class GestureDraft:
    """Keep unfinished command text separate from a validated definition."""

    criteria: GestureMatch
    commands: str
    delay: str
    tracking: GestureTrackingSettings = GestureTrackingSettings()
    repeat: MovementSettingsDraft = MovementSettingsDraft.defaults()
    use_optimistic_tracking: bool = True

    @classmethod
    def from_definition(cls, definition: GestureDefinition):
        return cls(
            criteria=definition.match,
            commands=", ".join(step.value for step in definition.commands.steps),
            delay=str(definition.commands.delay_ms_between_steps),
            tracking=definition.tracking,
            repeat=MovementSettingsDraft.from_settings(definition.repeat_settings),
            use_optimistic_tracking=definition.use_optimistic_tracking,
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
        try:
            repeat_settings = self.repeat.to_settings()
        except ValueError as error:
            raise ValueError(f"{definition.name}: {error}") from error
        return replace(
            definition, match=self.criteria, commands=sequence, tracking=self.tracking,
            repeat_settings=repeat_settings,
            use_optimistic_tracking=self.use_optimistic_tracking,
        )
