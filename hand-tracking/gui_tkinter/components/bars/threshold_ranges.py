"""Deviation boundary data and editing rules independent of Tkinter."""

from gestures.finger_thresholds import MAX_DEVIATION_DEGREES, FingerThresholds, splits_are_valid


class ThresholdRanges:
    """Own increasing split points without making the view handle validation."""

    def __init__(self, thresholds, segment_count, maximum=MAX_DEVIATION_DEGREES):
        self.maximum = maximum
        self.set_ranges(thresholds, segment_count)

    @property
    def thresholds(self):
        return list(self._thresholds)

    def set_ranges(self, thresholds, segment_count):
        ranges = FingerThresholds(tuple(float(value) for value in thresholds), segment_count)
        if not ranges.is_valid or not splits_are_valid(ranges.splits, self.maximum):
            raise ValueError("Deviation ranges need increasing split points for 4–6 segments")
        self._thresholds = list(ranges.splits)
        self.categories = ranges.categories

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
