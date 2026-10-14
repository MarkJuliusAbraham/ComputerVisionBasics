"""The single description of MediaPipe's 21-point hand model.

Landmark indices, finger joint chains, finger names, and handedness labels
are defined here once. Detection, drawing, validation, and the UI read them
from this module instead of keeping their own copies.
"""

from enum import IntEnum


class Landmark(IntEnum):
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12
    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20


# Each chain runs from the finger's base joint to its tip, in display order.
FINGER_JOINTS: dict[str, tuple[Landmark, Landmark, Landmark, Landmark]] = {
    "thumb": (Landmark.THUMB_CMC, Landmark.THUMB_MCP, Landmark.THUMB_IP, Landmark.THUMB_TIP),
    "index": (Landmark.INDEX_MCP, Landmark.INDEX_PIP, Landmark.INDEX_DIP, Landmark.INDEX_TIP),
    "middle": (Landmark.MIDDLE_MCP, Landmark.MIDDLE_PIP, Landmark.MIDDLE_DIP, Landmark.MIDDLE_TIP),
    "ring": (Landmark.RING_MCP, Landmark.RING_PIP, Landmark.RING_DIP, Landmark.RING_TIP),
    "pinky": (Landmark.PINKY_MCP, Landmark.PINKY_PIP, Landmark.PINKY_DIP, Landmark.PINKY_TIP),
}
FINGER_NAMES: tuple[str, ...] = tuple(FINGER_JOINTS)
KNUCKLES = (Landmark.INDEX_MCP, Landmark.MIDDLE_MCP, Landmark.RING_MCP, Landmark.PINKY_MCP)

# MediaPipe's handedness categories, in the order hands are displayed.
HANDEDNESS: tuple[str, ...] = ("Left", "Right")


def finger_label(name: str) -> str:
    return name.title()


def point(landmark) -> tuple[float, float, float]:
    """Copy a MediaPipe landmark into a plain (x, y, z) tuple."""
    return (landmark.x, landmark.y, landmark.z)
