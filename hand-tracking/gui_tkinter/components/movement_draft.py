"""Shared editable movement settings, including unfinished numeric input.

Forms keep the text the user typed; these helpers convert between that text
and the validated settings records in one place.
"""

from dataclasses import dataclass

from gestures.repeating.settings import AXES, AxisWeights, MovementBufferSettings, RepeatSettings


def number_text(value):
    """Display a stored number without float noise (0.30000000000000004 -> 0.3)."""
    return format(value, ".12g")


def percent_text(fraction):
    return number_text(fraction * 100)


def parse_numbers(texts, message):
    """Convert every entry to float, reporting one message for any bad entry."""
    try:
        return {name: float(text) for name, text in texts.items()}
    except (TypeError, ValueError) as error:
        raise ValueError(message) from error


def buffer_texts(movement: MovementBufferSettings, axes=AXES):
    """Form text for the starting buffer, its credit, and the chosen axes."""
    return {
        "buffer": percent_text(movement.initial_displacement),
        "credit": percent_text(movement.buffer_credit),
        **{axis: number_text(getattr(movement.axis_weights, axis)) for axis in axes},
    }


def buffer_from_numbers(numbers, axes=AXES) -> MovementBufferSettings:
    """Build buffer settings from parsed form numbers (percentages for the buffer)."""
    return MovementBufferSettings(
        initial_displacement=numbers["buffer"] / 100,
        buffer_credit=numbers["credit"] / 100,
        axis_weights=AxisWeights(**{axis: numbers[axis] for axis in axes}),
    )


@dataclass(frozen=True)
class MovementSettingsDraft:
    distance: str
    buffer: str
    credit: str
    limit: str
    x: str
    y: str
    z: str
    min_interval_seconds: float

    @classmethod
    def defaults(cls):
        return cls.from_settings(RepeatSettings())

    @classmethod
    def from_settings(cls, settings):
        return cls(
            distance=percent_text(settings.distance_threshold),
            limit=str(settings.max_repeats),
            min_interval_seconds=settings.min_interval_seconds,
            **buffer_texts(settings.movement),
        )

    def to_settings(self):
        try:
            limit = int(self.limit)
        except ValueError as error:
            raise ValueError("Repeat limit must be a whole number") from error
        numbers = parse_numbers(
            {"distance": self.distance, "buffer": self.buffer, "credit": self.credit,
             **{axis: getattr(self, axis) for axis in AXES}},
            "Repeat distances, buffer credit, and axis weights must be numbers",
        )
        return RepeatSettings(
            distance_threshold=numbers["distance"] / 100,
            max_repeats=limit,
            min_interval_seconds=self.min_interval_seconds,
            movement=buffer_from_numbers(numbers),
        )
