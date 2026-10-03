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
    tip: tuple[float, float]


FINGERS = {
    "thumb": (1, 2, 3, 4),
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}


class FingerClassifier:
    STRAIGHT_THRESHOLD = 15.0
    CURLED_THRESHOLD = 45.0
    CLOSED_THRESHOLD = 75.0

    def classify(self, hand, indices) -> FingerState:
        mcp, pip, dip, tip = (
            hand[i]
            for i in indices
        )

        deviation = self.deviation(hand, indices)

        if deviation <= self.STRAIGHT_THRESHOLD:
            position = FingerPosition.STRAIGHT
        elif deviation >= self.CLOSED_THRESHOLD:
            position = FingerPosition.CLOSED
        elif deviation >= self.CURLED_THRESHOLD:
            position = FingerPosition.CURLED
        else:
            position = FingerPosition.PARTIAL

        return FingerState(
            deviation=deviation,
            position=position,
            tip=(tip.x, tip.y),
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
