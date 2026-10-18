"""Detect backtracking by comparing traveled distance with net displacement."""

from collections import deque
from math import dist, isfinite


def average_distance(start, end):
    """Average individual landmark travel; opposite motions must not cancel."""
    return sum(dist(a, b) for a, b in zip(start, end)) / len(start)


class HandShakeDetector:
    """Require enough travel and a return close to the motion's origin.

    Wrist and all available fingertips contribute equally. Individual distances
    are averaged, so opposing fingertip movements cannot cancel. The configured
    travel threshold is measured in palm widths. A return within
    one quarter of that distance counts as close. A minimum excursion rejects
    tiny stationary jitter. Each repeat consumes the path once; the command
    remains remembered by the gesture controller.
    """

    def __init__(self, settings, frame_aspect=1.0):
        self.settings = settings
        self.aspect = frame_aspect
        self._samples = deque(maxlen=256)
        self._palm_size = None
        self._origin = None
        self._point_names = ()

    def observe(self, wrist, palm_size, now, fingertips=None):
        landmarks = {"wrist": wrist, **(fingertips or {})}
        if (wrist is None or not all(isfinite(v) for v in wrist)
                or palm_size is None or not isfinite(palm_size) or palm_size <= 0
                or any(p is None or not all(isfinite(v) for v in p) for p in landmarks.values())):
            self._samples.clear()
            self._palm_size = None
            self._origin = None
            return False
        names = tuple(sorted(landmarks))
        if names != self._point_names:
            # Do not compare different groups or connect a returning fingertip
            # to a stale position. Command memory lives outside this detector.
            self._samples.clear()
            self._origin = None
            self._point_names = names
        point = tuple(
            (landmarks[name][0], landmarks[name][1] * self.aspect, landmarks[name][2])
            for name in names
        )
        cutoff = now - self.settings.shake_window_seconds
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()
        if not self._samples:
            self._palm_size = palm_size
            if self._origin is None:
                self._origin = point
            self._samples.append((now, point))
            return False
        # Spatial deadband: tiny landmark jitter cannot accumulate path length.
        if average_distance(self._samples[-1][1], point) < self._palm_size * 0.05:
            return False
        self._samples.append((now, point))
        points = [sample[1] for sample in self._samples]
        traveled = sum(average_distance(a, b) for a, b in zip(points, points[1:]))
        displacement = average_distance(self._origin, points[-1])
        required = self.settings.shake_amplitude * self._palm_size
        return_radius = required * 0.25
        excursion = max(average_distance(self._origin, point) for point in points)
        if (traveled + 1e-12 < required or displacement > return_radius
                or excursion < required * 0.5):
            return False
        # Consume this motion: the same path cannot generate another repeat.
        self._samples.clear()
        self._samples.append((now, point))
        self._palm_size = palm_size
        self._origin = point
        return True
