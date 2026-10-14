"""Capture-worker status shared with the UI without importing OpenCV."""

from dataclasses import dataclass
from enum import Enum


class CameraPhase(str, Enum):
    OPENING = "opening"
    SWITCHING = "switching"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True)
class CameraStatus:
    """The capture worker's latest state, published to the UI as one value."""

    phase: CameraPhase
    requested_index: int
    active_index: int | None
    message: str | None = None

    @property
    def is_switching(self) -> bool:
        return self.phase in (CameraPhase.OPENING, CameraPhase.SWITCHING)
