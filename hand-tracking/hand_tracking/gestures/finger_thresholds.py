"""The rules for finger deviation split points, owned in one place.

Settings persistence, the editable deviation scale, the live preview, and
the debugging displays all use these defaults, limits, and checks.
"""

from dataclasses import dataclass

from .finger_classifier import FINGER_CATEGORIES_BY_COUNT, FingerClassifier, finger_categories

MAX_DEVIATION_DEGREES = 120.0
DEFAULT_SPLITS = (15.0, 45.0, 75.0)


def splits_are_valid(values, maximum=MAX_DEVIATION_DEGREES) -> bool:
    """Every split lies within 0..maximum and the splits strictly increase."""
    return all(0.0 <= value <= maximum for value in values) and all(
        left < right for left, right in zip(values, values[1:])
    )


def resize_finger_thresholds(thresholds, segment_count):
    """Resize a split list while retaining existing values where practical."""
    if segment_count not in FINGER_CATEGORIES_BY_COUNT:
        raise ValueError("Finger segment count must be between 4 and 6")
    values = sorted(float(value) for value in thresholds)
    if len(values) < 2:
        values = list(DEFAULT_SPLITS)
    target_count = segment_count - 1
    while len(values) < target_count:
        insert_before_closed = len(values) - 1
        lower = values[insert_before_closed - 1]
        upper = values[insert_before_closed]
        values.insert(insert_before_closed, (lower + upper) / 2)
    while len(values) > target_count:
        if target_count == 0:
            return []
        # Added bands are inserted immediately before the Closed band, so
        # remove those split points in reverse order when reducing the count.
        values.pop(-2)
    return values


@dataclass(frozen=True)
class FingerThresholds:
    """Ordered deviation split points and the number of bands they create."""

    splits: tuple[float, ...]
    segment_count: int = 4

    @classmethod
    def defaults(cls, segment_count=4):
        """Keep the original four bands and subdivide the higher-bend ranges."""
        return cls(tuple(resize_finger_thresholds(DEFAULT_SPLITS, segment_count)), segment_count)

    @property
    def is_valid(self) -> bool:
        return (
            self.segment_count in FINGER_CATEGORIES_BY_COUNT
            and len(self.splits) == self.segment_count - 1
            and splits_are_valid(self.splits)
        )

    @property
    def categories(self):
        return finger_categories(self.segment_count)

    @property
    def max_deviation(self) -> float:
        """The last split: deviations past it are fully bent for display."""
        return self.splits[-1]

    def classify(self, deviation):
        return FingerClassifier.classify_deviation(deviation, self.splits, self.categories)


def default_finger_thresholds(segment_count=4):
    return list(FingerThresholds.defaults(segment_count).splits)

