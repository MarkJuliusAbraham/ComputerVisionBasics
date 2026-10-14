from enum import Enum

from .geometry import cross, vector
from .hand_landmarks import Landmark


class PalmPosition(Enum):
    FACING_CAMERA = "facing_camera"
    NOT_FACING_CAMERA = "not_facing_camera"

    @property
    def label(self) -> str:
        """Sentence-case display text, e.g. "Not facing camera"."""
        return self.value.replace("_", " ").capitalize()


class PalmDetector:
    def detect(
        self,
        hand,
        handedness: str,
        aspect: float = 1.0,
    ) -> PalmPosition:
        wrist = hand[Landmark.WRIST]
        index = hand[Landmark.INDEX_MCP]
        pinky = hand[Landmark.PINKY_MCP]

        v1 = vector(wrist, index, aspect)
        v2 = vector(wrist, pinky, aspect)

        normal_z = cross(v1, v2)[2]

        facing = (
            normal_z < 0
            if handedness == "Right"
            else normal_z > 0
        )

        return (
            PalmPosition.FACING_CAMERA
            if facing
            else PalmPosition.NOT_FACING_CAMERA
        )
