"""Serializable settings for movement-triggered command repeats."""

import math
from dataclasses import dataclass


def validate_number(value, label, minimum=0):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if value < minimum:
        raise ValueError(f"{label} must be at least {minimum}")


@dataclass(frozen=True)
class AxisWeights:
    x: float = 1.0
    y: float = 1.0
    z: float = 0.0

    def __post_init__(self):
        for name in ("x", "y", "z"):
            validate_number(getattr(self, name), f"{name.upper()} axis weight")

    def to_dict(self):
        return {name: getattr(self, name) for name in ("x", "y", "z")}

    @classmethod
    def from_dict(cls, value):
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError("Axis weights must be an object")
        defaults = cls()
        return cls(**{name: value.get(name, getattr(defaults, name)) for name in ("x", "y", "z")})


def validate_movement_buffer(settings):
    validate_number(settings.initial_displacement, "Starting buffer")
    validate_number(settings.buffer_credit, "Buffer credit")
    if settings.buffer_credit > 1:
        raise ValueError("Buffer credit must be between 0% and 100%")
    if not isinstance(settings.axis_weights, AxisWeights):
        raise ValueError("Axis weights must be an AxisWeights object")


@dataclass(frozen=True)
class MovementBufferSettings:
    initial_displacement: float = 0.03
    buffer_credit: float = 0.0
    axis_weights: AxisWeights = AxisWeights()

    def __post_init__(self):
        validate_movement_buffer(self)

    @classmethod
    def from_dict(cls, value):
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError("Movement settings must be an object")
        defaults = cls()
        return cls(
            initial_displacement=value.get("initial_displacement", defaults.initial_displacement),
            buffer_credit=value.get("buffer_credit", defaults.buffer_credit),
            axis_weights=AxisWeights.from_dict(value.get("axis_weights")),
        )


@dataclass(frozen=True)
class RepeatSettings:
    initial_displacement: float = 0.03
    distance_threshold: float = 0.09
    min_interval_seconds: float = 0.05
    max_repeats: int = 2
    axis_weights: AxisWeights = AxisWeights()
    buffer_credit: float = 0.0

    def __post_init__(self):
        validate_movement_buffer(self)
        validate_number(self.distance_threshold, "Distance per repeat")
        if self.distance_threshold == 0:
            raise ValueError("Distance per repeat must be greater than zero")
        validate_number(self.min_interval_seconds, "Repeat interval")
        if not isinstance(self.max_repeats, int) or isinstance(self.max_repeats, bool) or self.max_repeats < 0:
            raise ValueError("Repeat limit must be a non-negative whole number")
        if self.max_repeats and not any(self.axis_weights.to_dict().values()):
            raise ValueError("At least one axis weight must be greater than zero")

    def to_dict(self):
        return {
            "initial_displacement": self.initial_displacement,
            "distance_threshold": self.distance_threshold,
            "min_interval_seconds": self.min_interval_seconds,
            "max_repeats": self.max_repeats,
            "axis_weights": self.axis_weights.to_dict(),
            "buffer_credit": self.buffer_credit,
        }

    @classmethod
    def from_dict(cls, value):
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError("repeat_settings must be an object")
        defaults = cls()
        return cls(
            initial_displacement=value.get("initial_displacement", defaults.initial_displacement),
            distance_threshold=value.get("distance_threshold", defaults.distance_threshold),
            min_interval_seconds=value.get("min_interval_seconds", defaults.min_interval_seconds),
            max_repeats=value.get("max_repeats", defaults.max_repeats),
            axis_weights=AxisWeights.from_dict(value.get("axis_weights")),
            buffer_credit=value.get("buffer_credit", defaults.buffer_credit),
        )
