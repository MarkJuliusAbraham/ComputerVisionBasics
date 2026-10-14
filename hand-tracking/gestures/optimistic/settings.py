"""Persisted wrist history and movement-repeat settings."""

from dataclasses import dataclass, replace
from typing import ClassVar

from config_values import merged_fields, validate_number
from gestures.repeating.settings import MovementBufferSettings


@dataclass(frozen=True)
class OptimisticTrackingSettings:
    QUALIFIED_REPEAT_COUNT: ClassVar[int] = 2
    enabled: bool = True
    lookback_seconds: float = 0.5
    activation_distance: float = 0.09
    repeat_delay_ms: float = 50.0
    delay_variance_ms: float = 0.0
    movement: MovementBufferSettings = MovementBufferSettings()

    def __post_init__(self):
        if not isinstance(self.enabled, bool):
            raise ValueError("Optimistic tracking enabled must be a boolean")
        validate_number(self.lookback_seconds, "Wrist lookback duration")
        validate_number(self.activation_distance, "Wrist activation distance")
        if self.lookback_seconds == 0 or self.activation_distance == 0:
            raise ValueError("Wrist lookback duration and activation distance must be greater than zero")
        validate_number(self.repeat_delay_ms, "Repeat delay")
        validate_number(self.delay_variance_ms, "Delay variance")
        if not isinstance(self.movement, MovementBufferSettings):
            raise ValueError("Optimistic movement must contain valid buffer and axis settings")

    @classmethod
    def from_dict(cls, value):
        if isinstance(value, cls):
            return value
        values = merged_fields(
            cls, value, "optimistic_tracking",
            ("enabled", "lookback_seconds", "delay_variance_ms"),
        )
        value = value or {}
        raw_movement = value.get("movement") or {}
        movement = MovementBufferSettings.from_dict(raw_movement)
        # Wrist motion is measured in the image plane only.
        movement = replace(movement, axis_weights=replace(movement.axis_weights, z=0.0))
        # Preserve saved thresholds and delays from the previous repeat-style
        # format. Wrist motion now grants one fixed burst on activation.
        legacy_delay = raw_movement.get("min_interval_seconds", cls.repeat_delay_ms / 1000)
        validate_number(legacy_delay, "Repeat delay")
        return cls(
            **values,
            activation_distance=value.get(
                "activation_distance", raw_movement.get("distance_threshold", cls.activation_distance),
            ),
            repeat_delay_ms=value.get("repeat_delay_ms", legacy_delay * 1000),
            movement=movement,
        )
