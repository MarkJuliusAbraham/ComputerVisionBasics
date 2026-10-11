import math
from dataclasses import dataclass
from enum import Enum

from .geometry import angle


class FingerPosition(Enum):
    STRAIGHT = "straight"
    PARTIAL = "partial"
    CURLED = "curled"
    CLOSED = "closed"


@dataclass(frozen=True)
class FingerState:
    deviation: float
    position: FingerPosition
    tip: tuple[float, float, float]


FINGERS = {
    "thumb": (1, 2, 3, 4),
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}


class FingerClassifier:
    def __init__(self, straight_threshold, curled_threshold, closed_threshold):
        self.straight_threshold = straight_threshold
        self.curled_threshold = curled_threshold
        self.closed_threshold = closed_threshold

    def classify(self, hand, indices) -> FingerState:
        mcp, pip, dip, tip = (
            hand[i]
            for i in indices
        )

        deviation = self.deviation(hand, indices)

        if deviation <= self.straight_threshold:
            position = FingerPosition.STRAIGHT
        elif deviation >= self.closed_threshold:
            position = FingerPosition.CLOSED
        elif deviation >= self.curled_threshold:
            position = FingerPosition.CURLED
        else:
            position = FingerPosition.PARTIAL

        return FingerState(
            deviation=deviation,
            position=position,
            tip=(tip.x, tip.y, tip.z),
        )

    def classify_all(self, hand) -> dict[str, FingerState]:
        return {
            name: self.classify(hand, indices)
            for name, indices in FINGERS.items()
        }

    def deviation(self, hand, indices) -> float:
        mcp, pip, dip, tip = (
            hand[i]
            for i in indices
        )

        pip_deviation = abs(
            180.0 - angle(mcp, pip, dip)
        )
        dip_deviation = abs(
            180.0 - angle(pip, dip, tip)
        )

        return math.hypot(
            pip_deviation,
            dip_deviation,
        ) / math.sqrt(2)
