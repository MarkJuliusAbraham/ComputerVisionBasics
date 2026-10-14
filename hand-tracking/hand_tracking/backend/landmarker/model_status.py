"""Portable runtime model information shared with the debugging UI."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ModelPhase(str, Enum):
    EMPTY = "empty"
    LOADING = "loading"
    READY = "ready"
    FAILED = "failed"


class ModelCondition(Enum):
    """What the UI should tell the user; combines the phase with availability."""

    LOADING = "loading"
    FAILED = "failed"
    MISSING = "missing"
    READY = "ready"


@dataclass(frozen=True)
class ModelStatus:
    phase: ModelPhase = ModelPhase.EMPTY
    requested_path: str = ""
    active_path: str = ""
    message: str = ""

    @property
    def available(self):
        return bool(self.active_path)

    @property
    def can_detect(self):
        return self.available and self.phase != ModelPhase.LOADING

    @property
    def name(self):
        return Path(self.active_path).name if self.available else "No model loaded"

    @property
    def condition(self) -> ModelCondition:
        if self.phase == ModelPhase.LOADING:
            return ModelCondition.LOADING
        if self.phase == ModelPhase.FAILED:
            return ModelCondition.FAILED
        return ModelCondition.READY if self.available else ModelCondition.MISSING

    @property
    def needs_attention(self):
        """A failed load, or no model to detect with (including while loading one)."""
        return self.phase == ModelPhase.FAILED or not self.available

    @property
    def tracking_block_reason(self):
        if self.phase == ModelPhase.LOADING:
            return "Loading landmarker model…"
        return "No landmarker model loaded" if not self.available else ""
