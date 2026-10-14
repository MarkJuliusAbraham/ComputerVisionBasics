"""Average weighted fingertip movement with one shared displacement buffer."""

import math
from dataclasses import dataclass

from hand_tracking.gestures.tracking.path import PathSegment, Point


def interpolate(start, end, fraction):
    return tuple(a + (b - a) * fraction for a, b in zip(start, end))


class WeightedDistance:
    def __init__(self, weights, frame_aspect=1.0):
        self.scales = (weights.x, weights.y * frame_aspect, weights.z)

    def delta(self, start, end):
        return tuple((b - a) * scale for a, b, scale in zip(start, end, self.scales))

    def length(self, start, end):
        return math.hypot(*self.delta(start, end))

    def average_length(self, segments):
        return math.fsum(self.length(segment.start, segment.end) for segment in segments.values()) / len(segments)

    def average_displacement(self, origins, segments, fraction):
        return math.fsum(
            self.length(origins[name], interpolate(segment.start, segment.end, fraction))
            for name, segment in segments.items()
        ) / len(origins)

    def buffer_crossing(self, origins, segments, radius):
        if self.average_displacement(origins, segments, 1.0) < radius:
            return None
        if self.average_displacement(origins, segments, 0.0) >= radius:
            return 0.0
        # The mean of several displacement lengths has no single quadratic
        # solution. Locate its shared exit from the buffer within this frame.
        lower, upper = 0.0, 1.0
        for _ in range(40):
            middle = (lower + upper) / 2
            if self.average_displacement(origins, segments, middle) < radius:
                lower = middle
            else:
                upper = middle
        return upper


@dataclass(frozen=True)
class RepeatCrossing:
    """All fingertip marker positions for one shared repeat event."""

    fraction: float
    markers: tuple[tuple[str, Point], ...]


@dataclass(frozen=True)
class DistanceAdvance:
    before: float
    after: float
    segments: dict[str, PathSegment]
    start_fraction: float

    def crossing(self, distance):
        # Credited buffer distance becomes eligible at the buffer boundary.
        fraction = 0.0 if distance <= self.before else (distance - self.before) / (self.after - self.before)
        fraction = min(1.0, max(0.0, fraction))
        shared_fraction = self.start_fraction + (1 - self.start_fraction) * fraction
        return RepeatCrossing(
            shared_fraction,
            tuple(
                (name, interpolate(segment.start, segment.end, shared_fraction))
                for name, segment in self.segments.items()
            ),
        )


class AverageDistanceAccumulator:
    """``settings`` is a MovementBufferSettings: the starting buffer and its credit."""

    def __init__(self, origins, metric, settings):
        self.origins = dict(origins)
        self.metric = metric
        self.settings = settings
        self.armed = settings.initial_displacement == 0
        self.distance = 0.0
        self._rebase_next = False

    def advance(self, segments):
        # Keep the selected group fixed. Missing samples must not change the
        # denominator or count an unobserved jump when a fingertip returns.
        if not self.origins.keys() <= segments.keys():
            self._rebase_next = True
            return None
        tracked = {name: segments[name] for name in self.origins}
        if self._rebase_next:
            self._rebase_next = False
            return None
        movement = self.metric.average_length(tracked)
        if movement == 0:
            return None
        fraction = 0.0
        if not self.armed:
            fraction = self.metric.buffer_crossing(
                self.origins, tracked, self.settings.initial_displacement,
            )
            if fraction is None:
                return None
            self.armed = True
            self.distance = self.settings.initial_displacement * self.settings.buffer_credit
        before = self.distance
        self.distance += movement * (1 - fraction)
        return DistanceAdvance(before, self.distance, tracked, fraction)
