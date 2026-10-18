"""Stateful category boundaries, independent of gesture definitions."""

from dataclasses import replace


class FingerHysteresis:
    def __init__(self, thresholds, categories, margin_degrees=0):
        self.thresholds = tuple(thresholds)
        self.categories = tuple(categories)
        self.margin = margin_degrees
        self._hands = {}

    def reset(self):
        self._hands.clear()

    def finish_frame(self, present_hands):
        self._hands = {name: fingers for name, fingers in self._hands.items()
                       if name in present_hands}

    def apply(self, handedness, fingers):
        if self.margin <= 0:
            return fingers
        previous = self._hands.setdefault(handedness, {})
        output = {}
        for name, state in fingers.items():
            index = previous.get(name)
            if index is None:
                index = self.categories.index(state.position)
            else:
                # Strict crossings preserve the current category at either edge.
                # Loops allow deliberate large bends to skip several bands.
                while index < len(self.thresholds) and state.deviation > self.thresholds[index] + self.margin:
                    index += 1
                while index > 0 and state.deviation < self.thresholds[index - 1] - self.margin:
                    index -= 1
            previous[name] = index
            output[name] = replace(state, position=self.categories[index])
        return output
