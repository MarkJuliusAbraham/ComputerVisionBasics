"""Widget-independent formatting shared by hand reports and the overlay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from hand_tracking.gestures.hand_report import HandReport

if TYPE_CHECKING:
    from hand_tracking.gestures.gesture_config import CommandSequence


@dataclass(frozen=True)
class HandSummaryData:
    status: str = "Not detected"
    palm: str = "—"
    gesture: str = "—"
    command: str = "—"

    @classmethod
    def from_record(cls, record: HandReport | None) -> HandSummaryData:
        if record is None:
            return cls()
        gesture = record.gesture
        return cls(
            "Detected", record.state.palm.label.title(),
            gesture.name if gesture else "—",
            cls.describe_commands(gesture.commands) if gesture else "—",
        )

    @staticmethod
    def describe_commands(sequence: CommandSequence) -> str:
        key_names = {" ": "Space", "\t": "Tab", "\n": "Enter", "\r": "Enter"}
        return " → ".join(key_names.get(step.value, step.value) for step in sequence.steps)

    @property
    def fields(self) -> tuple[tuple[str, str], ...]:
        return (
            ("Status", self.status), ("Palm", self.palm),
            ("Gesture", self.gesture), ("Command", self.command),
        )
