import math
from bisect import bisect_right
from dataclasses import dataclass

from .geometry import angle
from .hand_landmarks import FINGER_JOINTS, point


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
# Every category in display order; the largest segment count contains them all.
ALL_FINGER_CATEGORIES = FINGER_CATEGORIES_BY_COUNT[max(FINGER_CATEGORIES_BY_COUNT)]
FINGER_POSITIONS = frozenset(category.value for category in ALL_FINGER_CATEGORIES)


def finger_categories(segment_count=4):
    return FINGER_CATEGORIES_BY_COUNT.get(segment_count, FINGER_CATEGORIES)


@dataclass(frozen=True)
class FingerState:
    deviation: float
    position: FingerCategory
    tip: tuple[float, float, float]


class FingerClassifier:
    CALCULATION_DEFAULT = "default"
    CALCULATION_PROTOTYPE = "prototype"
    CALCULATIONS = (CALCULATION_DEFAULT, CALCULATION_PROTOTYPE)

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

    def classify(self, hand, indices, aspect=1.0) -> FingerState:
        deviation = self.deviation(hand, indices, aspect)
        position = self.classify_deviation(
            deviation, self.thresholds, self.categories
        )
        return FingerState(
            deviation=deviation,
            position=position,
            tip=point(hand[indices[-1]]),
        )

    def classify_all(self, hand, aspect=1.0) -> dict[str, FingerState]:
        return {
            name: self.classify(hand, joints, aspect)
            for name, joints in FINGER_JOINTS.items()
        }

    def deviation(self, hand, indices, aspect=1.0) -> float:
        mcp, pip, dip, tip = (hand[i] for i in indices)
        pip_deviation = abs(180.0 - angle(mcp, pip, dip, aspect))
        dip_deviation = abs(180.0 - angle(pip, dip, tip, aspect))

        if self.calculation == self.CALCULATION_PROTOTYPE:
            # Experimental, intentionally aggressive: a strong bend at either
            # joint is enough to raise the score instead of being averaged down.
            return max(pip_deviation, dip_deviation)
        return math.hypot(pip_deviation, dip_deviation) / math.sqrt(2)
