"""Build gesture criteria from a pose the user holds in front of the camera.

Teaching by example avoids guessing which classification band each finger
falls in. Each finger takes the band it held for most of the capture, so a
brief flicker near a threshold does not widen the rule. A finger shown fully
straight or fully closed usually means "resembles this", so an allowance
extends those extreme bands toward the middle: with an allowance of one band,
a straight finger also accepts partial. Middle bands stay exact. The palm is
constrained only when it was consistent across the capture.
"""

from collections import Counter

from .finger_classifier import finger_categories
from .gesture_config import GestureMatch
from .hand_landmarks import FINGER_NAMES
from .hand_report import HandReport


class PoseCapture:
    """Accumulate one hand's reports and summarize them as a GestureMatch."""

    def __init__(self, segment_count=4, *, palm_agreement=0.8):
        self.order = tuple(category.value for category in finger_categories(segment_count))
        self.palm_agreement = palm_agreement
        self.handedness = None
        self.samples = 0
        self._fingers = {name: Counter() for name in FINGER_NAMES}
        self._palms = Counter()

    def add(self, report: HandReport) -> bool:
        """Count a report; the first hand seen is the only one captured."""
        if self.handedness is None:
            self.handedness = report.handedness
        elif report.handedness != self.handedness:
            return False
        state = report.state
        for name in FINGER_NAMES:
            finger = state.fingers.get(name)
            if finger is not None:
                self._fingers[name][finger.position.value] += 1
        self._palms[state.palm.value] += 1
        self.samples += 1
        return True

    def result(self, allowance=1) -> GestureMatch | None:
        """Criteria matching the captured pose, or None if no hand was seen.

        ``allowance`` is how many neighbouring bands a straight or closed
        finger also accepts.
        """
        if not self.samples:
            return None
        fingers = {}
        last = len(self.order) - 1
        for name, seen in self._fingers.items():
            indices = [self.order.index(value) for value in seen if value in self.order]
            if not indices:
                continue
            # The most frequent band; a tie goes to the straighter one.
            index = max(indices, key=lambda i: (seen[self.order[i]], -i))
            if index == 0:
                first, final = 0, min(allowance, last)
            elif index == last:
                first, final = max(last - allowance, 0), last
            else:
                first = final = index
            fingers[name] = frozenset(self.order[first:final + 1])
        palm, count = self._palms.most_common(1)[0]
        consistent = count / self.samples >= self.palm_agreement
        return GestureMatch(palm if consistent else None, fingers)
