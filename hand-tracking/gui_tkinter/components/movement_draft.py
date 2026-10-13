"""Shared editable movement settings, including unfinished numeric input."""

from dataclasses import dataclass

from gestures.repeating.settings import AxisWeights, RepeatSettings


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
            distance=format(settings.distance_threshold * 100, ".12g"),
            buffer=format(settings.initial_displacement * 100, ".12g"),
            credit=format(settings.buffer_credit * 100, ".12g"),
            limit=str(settings.max_repeats),
            x=str(settings.axis_weights.x), y=str(settings.axis_weights.y),
            z=str(settings.axis_weights.z),
            min_interval_seconds=settings.min_interval_seconds,
        )

    def to_settings(self):
        try:
            limit = int(self.limit)
        except ValueError as error:
            raise ValueError("Repeat limit must be a whole number") from error
        try:
            distance, buffer, credit, x, y, z = (
                float(value) for value in (self.distance, self.buffer, self.credit, self.x, self.y, self.z)
            )
        except ValueError as error:
            raise ValueError("Repeat distances, buffer credit, and axis weights must be numbers") from error
        return RepeatSettings(
            initial_displacement=buffer / 100,
            distance_threshold=distance / 100,
            buffer_credit=credit / 100,
            max_repeats=limit,
            axis_weights=AxisWeights(x=x, y=y, z=z),
            min_interval_seconds=self.min_interval_seconds,
        )
