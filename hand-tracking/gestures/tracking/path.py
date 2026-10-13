"""Bounded movement history and immutable drawing data for a single fingertip."""

from dataclasses import dataclass, field
from math import isfinite


Point = tuple[float, float, float]


@dataclass(frozen=True)
class PathSegment:
    start: Point
    end: Point


@dataclass(frozen=True)
class FingerDrawing:
    finger: str
    points: tuple[Point, ...]
    repeat_markers: tuple[Point, ...]


@dataclass
class FingertipPath:
    finger: str
    max_points: int
    points: list[Point] = field(default_factory=list)
    repeat_markers: list[Point] = field(default_factory=list)
    _snapshot: FingerDrawing | None = field(default=None, init=False, repr=False)

    def append(self, tip):
        point = (float(tip[0]), float(tip[1]), float(tip[2]))
        if not all(isfinite(value) for value in point):
            return None
        previous = self.points[-1] if self.points else point
        if self.points and point == previous:
            # Stationary fingertips still participate in average movement and
            # need a position for markers, without extending drawing history.
            return PathSegment(previous, point)
        self.points.append(point)
        if len(self.points) > self.max_points:
            self.points = self.points[::2]
            if self.points[-1] != point:
                self.points.append(point)
        self._snapshot = None
        return PathSegment(previous, point)

    def mark_repeat(self, point):
        self.repeat_markers.append(point)
        self._snapshot = None

    @property
    def drawing(self):
        if self._snapshot is None:
            self._snapshot = FingerDrawing(self.finger, tuple(self.points), tuple(self.repeat_markers))
        return self._snapshot
