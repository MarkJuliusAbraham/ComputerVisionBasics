"""One detected hand's classification and matched gesture for a single frame."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hand_tracking.backend.gestures.detector import GestureState
    from hand_tracking.backend.gestures.gesture_config import GestureDefinition


@dataclass(frozen=True)
class HandReport:
    handedness: str
    state: GestureState
    gesture: GestureDefinition | None = None

    @property
    def display_key(self):
        """The fields whose change should refresh the UI immediately."""
        return self.handedness, self.state.palm, self.gesture
