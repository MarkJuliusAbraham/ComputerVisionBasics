"""Portable runtime model information shared with the debugging UI."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelStatus:
    phase: str = "empty"
    requested_path: str = ""
    active_path: str = ""
    message: str = ""

    @property
    def available(self):
        return bool(self.active_path)

    @property
    def can_detect(self):
        return self.available and self.phase != "loading"

    @property
    def name(self):
        return Path(self.active_path).name if self.available else "No model loaded"

    @property
    def tracking_block_reason(self):
        if self.phase == "loading":
            return "Loading landmarker model…"
        return "No landmarker model loaded" if not self.available else ""
