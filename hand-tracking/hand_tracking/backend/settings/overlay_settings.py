"""Portable preferences for a tracking module's desktop overlay."""

from dataclasses import dataclass
from typing import Literal

from hand_tracking.backend.common.config_values import is_finite_number, merged_fields


OverlayStyle = Literal["Simple", "Pretty"]
OVERLAY_STYLES: tuple[OverlayStyle, ...] = ("Simple", "Pretty")
# What the overlay shows: the hand stats, or the camera picture above them.
OverlayContent = Literal["Stats", "Camera and stats"]
OVERLAY_CONTENTS: tuple[OverlayContent, ...] = ("Stats", "Camera and stats")
# Width of the camera-and-stats overlay; the stats-only overlay keeps its natural size.
OverlaySize = Literal["Small", "Medium", "Large"]
OVERLAY_SIZES: tuple[OverlaySize, ...] = ("Small", "Medium", "Large")


@dataclass(frozen=True)
class OverlayPosition:
    x: int
    y: int

    def __post_init__(self) -> None:
        if any(type(value) is not int for value in (self.x, self.y)):
            raise ValueError("Overlay coordinates must be integers.")
        if any(not -(1 << 31) <= value < (1 << 31) for value in (self.x, self.y)):
            raise ValueError("Overlay coordinates must fit desktop screen coordinates.")


@dataclass(frozen=True)
class OverlaySettings:
    style: OverlayStyle = "Pretty"
    background_opacity: float = 0.94
    position: OverlayPosition | None = None
    content: OverlayContent = "Stats"
    size: OverlaySize = "Medium"

    @property
    def shows_camera(self) -> bool:
        return self.content == "Camera and stats"

    def __post_init__(self) -> None:
        if self.style not in OVERLAY_STYLES:
            raise ValueError("Choose Simple or Pretty overlay style.")
        if not is_finite_number(self.background_opacity) or not 0 <= self.background_opacity <= 1:
            raise ValueError("Background opacity must be between 0% and 100%.")
        if self.position is not None and not isinstance(self.position, OverlayPosition):
            raise ValueError("Overlay position must contain screen coordinates.")
        if self.content not in OVERLAY_CONTENTS:
            raise ValueError("Choose what the overlay shows: Stats, or Camera and stats.")
        if self.size not in OVERLAY_SIZES:
            raise ValueError("Choose a Small, Medium or Large overlay.")

    @classmethod
    def from_dict(cls, value: object) -> "OverlaySettings":
        values = merged_fields(
            cls, value, "Overlay settings", ("style", "background_opacity", "content", "size"),
        )
        raw_position = (value or {}).get("position")
        if raw_position is None:
            position = None
        elif isinstance(raw_position, dict):
            position = OverlayPosition(raw_position.get("x"), raw_position.get("y"))
        else:
            raise ValueError("Overlay position must be an object.")
        return cls(**values, position=position)
