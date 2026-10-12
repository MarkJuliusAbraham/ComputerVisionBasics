"""Deviation boundary data and editing rules independent of Tkinter."""

from gestures.finger_classifier import FINGER_CATEGORIES_BY_COUNT, finger_categories


class ThresholdRanges:
    """Own increasing split points without making the view handle validation."""

    def __init__(self, thresholds, segment_count, maximum=120):
        self.maximum = maximum
        self.set_ranges(thresholds, segment_count)

    @property
    def thresholds(self):
        return list(self._thresholds)

    def set_ranges(self, thresholds, segment_count):
        values = [float(value) for value in thresholds]
        if (
            segment_count not in FINGER_CATEGORIES_BY_COUNT
            or len(values) != segment_count - 1
            or any(not 0 <= value <= self.maximum for value in values)
            or any(left >= right for left, right in zip(values, values[1:]))
        ):
            raise ValueError("Deviation ranges need increasing split points for 4–6 segments")
        self._thresholds = values
        self.categories = finger_categories(segment_count)

    def move(self, index, value):
        previous = self._thresholds[index - 1] if index else 0
        following = (
            self._thresholds[index + 1] if index < len(self._thresholds) - 1
            else self.maximum
        )
        gap = min(1.0, (following - previous) / 3)
        lower = previous + gap if index else 0
        upper = following - gap if index < len(self._thresholds) - 1 else self.maximum
        value = min(max(round(value, 1), lower), upper)
        if value == self._thresholds[index]:
            return False
        self._thresholds[index] = value
        return True
