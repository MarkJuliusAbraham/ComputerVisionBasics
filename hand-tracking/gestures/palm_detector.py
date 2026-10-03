from enum import Enum

from .geometry import cross, vector


class PalmPosition(Enum):
    FACING_CAMERA = "facing_camera"
    NOT_FACING_CAMERA = "not_facing_camera"


class PalmDetector:
    WRIST = 0
    INDEX_MCP = 5
    PINKY_MCP = 17

    def detect(
        self,
        hand,
        handedness: str,
    ) -> PalmPosition:
        wrist = hand[self.WRIST]
        index = hand[self.INDEX_MCP]
        pinky = hand[self.PINKY_MCP]

        v1 = vector(wrist, index)
        v2 = vector(wrist, pinky)

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
