"""Keep exact finger selections independent of their editing mode and layout."""

from ..criteria_options import (
    CUSTOM_CLASSIFICATIONS, FINGER_NAMES, FINGER_OPTIONS, FingerCriteriaOptions,
)


class FingerSelectionModel:
    """Own selected classification keys, including currently inactive keys."""

    def __init__(self, segment_count=4):
        self.options = FingerCriteriaOptions(segment_count)
        self.load({})

    def load(self, fingers):
        self._selections = {
            name: frozenset(fingers.get(name, ())) for name in FINGER_NAMES
        }

    def values(self):
        return self._selections.copy()

    def set_segment_count(self, segment_count):
        self.options = FingerCriteriaOptions(segment_count)

    def label_for(self, name):
        return next(
            (label for label, choices in self.options.simple_choices.items()
             if choices == self._selections[name]),
            CUSTOM_CLASSIFICATIONS,
        )

    def choose(self, name, label):
        if label == CUSTOM_CLASSIFICATIONS:
            return False
        return self._set(name, self.options.simple_choices[label])

    def set_checked(self, name, position, checked):
        selected = set(self._selections[name])
        if checked:
            selected.add(position)
        else:
            selected.discard(position)
        return self._set(name, frozenset(selected))

    def _set(self, name, selected):
        if self._selections[name] == selected:
            return False
        self._selections[name] = selected
        return True

    @property
    def inactive_positions(self):
        return self.options.inactive_selections(self._selections)

    @property
    def visible_positions(self):
        inactive = self.inactive_positions
        return tuple(
            position for position in FINGER_OPTIONS
            if position in self.options.positions or position in inactive
        )

    @property
    def availability_message(self):
        inactive = self.inactive_positions
        names = ", ".join(
            position.replace("_", " ") for position in FINGER_OPTIONS if position in inactive
        )
        detail = (
            f"Inactive: {names}. These cannot be detected at this segment count."
            if inactive else "All selected classifications are available."
        )
        return (
            f"{self.options.segment_count} segments. Saved classification selections are retained.\n"
            + detail
        )
