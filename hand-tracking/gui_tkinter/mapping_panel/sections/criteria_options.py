"""Choices shared by the two finger criteria editing modes."""

from gestures.finger_classifier import FINGER_CATEGORIES_BY_COUNT, FINGERS


PALM_OPTIONS = {
    "Any": None,
    "Facing camera": "facing_camera",
    "Not facing camera": "not_facing_camera",
}
FINGER_NAMES = tuple(FINGERS)
FINGER_OPTIONS = tuple(category.value for category in FINGER_CATEGORIES_BY_COUNT[6])
STRAIGHTNESS_OPTIONS = {
    "Any position": frozenset(),
    "Straight": frozenset(("straight",)),
    "Straight or Partial": frozenset(("straight", "partial")),
    "Closed": frozenset(("closed",)),
    "Closed or Curled": frozenset(("closed", "curled")),
    "Not Straight": frozenset(("partial", "curled", "closed")),
    "Not Closed": frozenset(("straight", "partial", "curled")),
}
CUSTOM_CLASSIFICATIONS = "Custom classifications"
