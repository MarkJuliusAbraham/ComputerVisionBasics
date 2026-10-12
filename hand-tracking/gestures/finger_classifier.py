import math
from bisect import bisect_right
from dataclasses import dataclass

from .geometry import angle


@dataclass(frozen=True)
class FingerCategory:
    """Stable key and display label for a deviation classification band."""

    value: str
    label: str
    gesture_class: str | None = None

    @property
    def semantic_class(self):
        return self.gesture_class or self.value


class FingerPosition:
    """Aliases for common categories referenced by gesture behavior."""

    STRAIGHT = FingerCategory("straight", "Straight")
    PARTIAL = FingerCategory("partial", "Partial")
    CURLED = FingerCategory("curled", "Curled")
    VERY_CURLED = FingerCategory("very_curled", "Very curled", "curled")
    NEARLY_CLOSED = FingerCategory("nearly_closed", "Nearly closed", "curled")
    CLOSED = FingerCategory("closed", "Closed")

FINGER_CATEGORIES_BY_COUNT = {
    4: (
        FingerPosition.STRAIGHT,
        FingerPosition.PARTIAL,
        FingerPosition.CURLED,
        FingerPosition.CLOSED,
    ),
    5: (
        FingerPosition.STRAIGHT,
        FingerPosition.PARTIAL,
        FingerPosition.CURLED,
        FingerPosition.VERY_CURLED,
        FingerPosition.CLOSED,
    ),
    6: (
        FingerPosition.STRAIGHT,
        FingerPosition.PARTIAL,
        FingerPosition.CURLED,
        FingerPosition.VERY_CURLED,
        FingerPosition.NEARLY_CLOSED,
        FingerPosition.CLOSED,
    ),
}
FINGER_CATEGORIES = FINGER_CATEGORIES_BY_COUNT[4]
FINGER_POSITIONS = {
    category.value
    for categories in FINGER_CATEGORIES_BY_COUNT.values()
    for category in categories
}


def finger_categories(segment_count=4):
    return FINGER_CATEGORIES_BY_COUNT.get(segment_count, FINGER_CATEGORIES)


@dataclass(frozen=True)
class FingerState:
    deviation: float
    position: FingerCategory
    tip: tuple[float, float, float]


FINGERS = {
    "thumb": (1, 2, 3, 4),
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}


class FingerClassifier:
    CALCULATION_DEFAULT = "default"
    CALCULATION_PROTOTYPE = "prototype"

    def __init__(
        self, thresholds, calculation=CALCULATION_DEFAULT, segment_count=4
    ):
        self.thresholds = tuple(float(value) for value in thresholds)
        self.calculation = calculation
        self.categories = finger_categories(segment_count)

    @staticmethod
    def classify_deviation(deviation, thresholds, categories=FINGER_CATEGORIES):
        """Map a score to an ordered category using N-1 split points."""
        if len(categories) == 1:
            return categories[0]
        if deviation <= thresholds[0]:
            return categories[0]
        # Split points after the first are inclusive, preserving the former
        # curled/closed boundary behavior.
        index = 1 + bisect_right(thresholds[1:], deviation)
        return categories[min(index, len(categories) - 1)]

    def classify(self, hand, indices) -> FingerState:
        _mcp, _pip, _dip, tip = (hand[i] for i in indices)
        deviation = self.deviation(hand, indices)
        position = self.classify_deviation(
            deviation, self.thresholds, self.categories
        )
        return FingerState(
            deviation=deviation,
            position=position,
            tip=(tip.x, tip.y, tip.z),
        )

    def classify_all(self, hand) -> dict[str, FingerState]:
        return {name: self.classify(hand, indices) for name, indices in FINGERS.items()}

    def deviation(self, hand, indices) -> float:
        mcp, pip, dip, tip = (hand[i] for i in indices)
        pip_deviation = abs(180.0 - angle(mcp, pip, dip))
        dip_deviation = abs(180.0 - angle(pip, dip, tip))

        if self.calculation == self.CALCULATION_PROTOTYPE:
            # Experimental, intentionally aggressive: a strong bend at either
            # joint is enough to raise the score instead of being averaged down.
            return max(pip_deviation, dip_deviation)
        return math.hypot(pip_deviation, dip_deviation) / math.sqrt(2)
