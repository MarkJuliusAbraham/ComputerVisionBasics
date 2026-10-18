"""Serializable settings for movement-triggered command repeats."""

from dataclasses import dataclass

from hand_tracking.backend.common.config_values import merged_fields, validate_number, validate_whole_number

AXES = ("x", "y", "z")


@dataclass(frozen=True)
class AxisWeights:
    x: float = 1.0
    y: float = 1.0
    z: float = 0.0

    def __post_init__(self):
        for name in AXES:
            validate_number(getattr(self, name), f"{name.upper()} axis weight")

    @property
    def any_positive(self):
        return any(getattr(self, name) for name in AXES)

    def to_dict(self):
        return {name: getattr(self, name) for name in AXES}

    @classmethod
    def from_dict(cls, value):
        return cls(**merged_fields(cls, value, "Axis weights"))


@dataclass(frozen=True)
class MovementBufferSettings:
    """How far tracked points must move before distance starts counting."""

    initial_displacement: float = 0.03
    buffer_credit: float = 0.0
    axis_weights: AxisWeights = AxisWeights()

    def __post_init__(self):
        validate_number(self.initial_displacement, "Starting buffer")
        validate_number(self.buffer_credit, "Buffer credit")
        if self.buffer_credit > 1:
            raise ValueError("Buffer credit must be between 0% and 100%")
        if not isinstance(self.axis_weights, AxisWeights):
            raise ValueError("Axis weights must be an AxisWeights object")

    def to_dict(self):
        return {
            "initial_displacement": self.initial_displacement,
            "buffer_credit": self.buffer_credit,
            "axis_weights": self.axis_weights.to_dict(),
        }

    @classmethod
    def from_dict(cls, value, label="Movement settings"):
        values = merged_fields(cls, value, label, ("initial_displacement", "buffer_credit"))
        return cls(**values, axis_weights=AxisWeights.from_dict((value or {}).get("axis_weights")))


@dataclass(frozen=True)
class RepeatSettings:
    distance_threshold: float = 0.09
    min_interval_seconds: float = 0.05
    max_repeats: int = 2
    movement: MovementBufferSettings = MovementBufferSettings()
    trigger: str = "tracking"
    shake_amplitude: float = 0.35  # Total travel per shake, in palm widths
    shake_window_seconds: float = 0.45

    def __post_init__(self):
        if self.trigger not in ("tracking", "distance", "shake"):
            raise ValueError("Repeat trigger must be tracking, distance, or shake")
        validate_number(self.shake_amplitude, "Shake travel", minimum=0.01)
        validate_number(self.shake_window_seconds, "Shake time window", minimum=0.01)
        if not isinstance(self.movement, MovementBufferSettings):
            raise ValueError("Repeat movement must contain valid buffer and axis settings")
        validate_number(self.distance_threshold, "Distance per repeat")
        if self.distance_threshold == 0:
            raise ValueError("Distance per repeat must be greater than zero")
        validate_number(self.min_interval_seconds, "Repeat interval")
        validate_whole_number(self.max_repeats, "Repeat limit must be a non-negative whole number")
        if self.trigger in ("tracking", "distance") and self.max_repeats and not self.movement.axis_weights.any_positive:
            raise ValueError("At least one axis weight must be greater than zero")

    def to_dict(self):
        # Profiles store the buffer fields alongside the repeat fields.
        movement = self.movement.to_dict()
        return {
            "trigger": self.trigger,
            "shake_amplitude": self.shake_amplitude,
            "shake_window_seconds": self.shake_window_seconds,
            "initial_displacement": movement["initial_displacement"],
            "distance_threshold": self.distance_threshold,
            "min_interval_seconds": self.min_interval_seconds,
            "max_repeats": self.max_repeats,
            "axis_weights": movement["axis_weights"],
            "buffer_credit": movement["buffer_credit"],
        }

    @classmethod
    def from_dict(cls, value):
        label = "repeat_settings"
        values = merged_fields(
            cls, value, label, (
                "distance_threshold", "min_interval_seconds", "max_repeats",
                "trigger", "shake_amplitude", "shake_window_seconds",
            ),
        )
        return cls(**values, movement=MovementBufferSettings.from_dict(value, label))
