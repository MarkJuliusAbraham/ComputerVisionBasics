"""Choices shared by the two finger criteria editing modes."""

from gestures.finger_classifier import ALL_FINGER_CATEGORIES, FINGER_CATEGORIES_BY_COUNT
from gestures.hand_landmarks import FINGER_NAMES
from gestures.palm_detector import PalmPosition


PALM_OPTIONS = {"Any": None, **{position.label: position.value for position in PalmPosition}}
# Stable profile keys include inactive classifications so saved rules survive
# changes to the detector's segment count.
FINGER_OPTIONS = tuple(category.value for category in ALL_FINGER_CATEGORIES)
CATEGORY_LABELS = {category.value: category.label for category in ALL_FINGER_CATEGORIES}
CUSTOM_CLASSIFICATIONS = "Custom classifications"

__all__ = [
    "CATEGORY_LABELS", "CUSTOM_CLASSIFICATIONS", "FINGER_NAMES", "FINGER_OPTIONS",
    "FingerCriteriaOptions", "PALM_OPTIONS",
]


class FingerCriteriaOptions:
    """Generate common choices without rewriting previously selected keys."""

    def __init__(self, segment_count=4):
        if segment_count not in FINGER_CATEGORIES_BY_COUNT:
            raise ValueError("Finger segment count must be between 4 and 6")
        self.segment_count = segment_count
        self.categories = FINGER_CATEGORIES_BY_COUNT[segment_count]
        self.positions = tuple(category.value for category in self.categories)
        self.simple_choices = {"Any position": frozenset()}
        for index, category in enumerate(self.categories):
            self.simple_choices[category.label.title()] = frozenset((category.value,))
            if index + 1 < len(self.categories):
                following = self.categories[index + 1]
                label = (
                    f"Closed or {category.label.title()}"
                    if following.value == "closed" else
                    f"{category.label.title()} or {following.label.title()}"
                )
                self.simple_choices[label] = frozenset((category.value, following.value))
        if segment_count > 4:
            self.simple_choices["Curled through Closed"] = frozenset(self.positions[2:])
        self.simple_choices["Not Straight"] = frozenset(self.positions[1:])
        self.simple_choices["Not Closed"] = frozenset(self.positions[:-1])

    def inactive_selections(self, selections):
        selected = set().union(*selections.values()) if selections else set()
        return selected.difference(self.positions)
