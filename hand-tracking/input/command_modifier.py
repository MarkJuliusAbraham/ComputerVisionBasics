"""Optional execution behavior attached to a recognized command sequence."""

from dataclasses import dataclass

from config_values import is_finite_number, validate_whole_number


@dataclass(frozen=True)
class CommandModifier:
    repeat_count: int = 0
    delay_seconds: float = 0.0
    delay_variance_seconds: float = 0.0

    def __post_init__(self):
        validate_whole_number(self.repeat_count, "Command repeat count must be a non-negative whole number")
        for value in (self.delay_seconds, self.delay_variance_seconds):
            if not is_finite_number(value) or value < 0:
                raise ValueError("Command repeat delay and variance must be finite non-negative numbers")

    def next_delay_seconds(self, random_uniform):
        if not self.delay_variance_seconds:
            return self.delay_seconds
        return random_uniform(
            max(0.0, self.delay_seconds - self.delay_variance_seconds),
            self.delay_seconds + self.delay_variance_seconds,
        )
