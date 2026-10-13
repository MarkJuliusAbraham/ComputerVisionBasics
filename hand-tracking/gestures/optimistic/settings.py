"""Persisted wrist history and movement-repeat settings."""

from dataclasses import dataclass
from typing import ClassVar

from gestures.repeating.settings import AxisWeights, MovementBufferSettings, validate_number


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
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError("optimistic_tracking must be an object")
        defaults = cls()
        raw_movement = value.get("movement") or {}
        movement = MovementBufferSettings.from_dict(raw_movement)
        # Preserve saved thresholds and delays from the previous repeat-style
        # format. Wrist motion now grants one fixed burst on activation.
        legacy_delay = raw_movement.get("min_interval_seconds", defaults.repeat_delay_ms / 1000)
        validate_number(legacy_delay, "Repeat delay")
        movement = MovementBufferSettings(
            initial_displacement=movement.initial_displacement,
            buffer_credit=movement.buffer_credit,
            axis_weights=AxisWeights(x=movement.axis_weights.x, y=movement.axis_weights.y),
        )
        return cls(
            enabled=value.get("enabled", defaults.enabled),
            lookback_seconds=value.get("lookback_seconds", defaults.lookback_seconds),
            activation_distance=value.get(
                "activation_distance", raw_movement.get("distance_threshold", defaults.activation_distance),
            ),
            repeat_delay_ms=value.get("repeat_delay_ms", legacy_delay * 1000),
            delay_variance_ms=value.get("delay_variance_ms", defaults.delay_variance_ms),
            movement=movement,
        )
