"""Bounded rolling wrist paths, measured with the same rules as fingertips."""

import math
import time
from collections import deque
from dataclasses import dataclass

from hand_tracking.gestures.repeating.distance import (
    AverageDistanceAccumulator,
    WeightedDistance,
    interpolate,
)
from hand_tracking.gestures.tracking.path import PathSegment, Point
from hand_tracking.input.command_modifier import CommandModifier

from .settings import OptimisticTrackingSettings


@dataclass(frozen=True)
class WristSample:
    time: float
    point: Point


class WristMovementHistory:
    def __init__(self, settings=None, *, clock=None):
        self.settings = settings if settings is not None else OptimisticTrackingSettings()
        self.clock = clock if clock is not None else time.monotonic
        self._hands = {}

    def configure(self, settings):
        if settings != self.settings:
            self.settings = settings
            self.clear()

    def clear(self):
        self._hands.clear()

    def finish_frame(self, present_hands):
        for hand in tuple(self._hands):
            if hand not in present_hands:
                del self._hands[hand]

    def consume(self, hand):
        """Use this motion once, retaining the latest point for new movement."""
        samples = self._hands.get(hand)
        if samples:
            self._hands[hand] = deque((samples[-1],))

    def record(self, hand, wrist):
        if wrist is None:
            self._hands.pop(hand, None)
            return
        if not self.settings.enabled:
            return
        point = tuple(float(value) for value in wrist)
        if len(point) != 3 or not all(math.isfinite(value) for value in point):
            self._hands.pop(hand, None)
            return
        now = self.clock()
        samples = self._hands.setdefault(hand, deque())
        if samples and now <= samples[-1].time:
            return
        if samples and now - samples[-1].time > self.settings.lookback_seconds:
            samples.clear()
        samples.append(WristSample(now, point))
        self._prune(samples, now - self.settings.lookback_seconds)

    @staticmethod
    def _prune(samples, cutoff):
        # Keep one sample before the boundary to interpolate the exact window.
        while len(samples) > 1 and samples[1].time <= cutoff:
            samples.popleft()

    def modifier_for(self, hand, frame_aspect=1.0):
        samples = self._hands.get(hand)
        if not self.settings.enabled or not samples or len(samples) < 2:
            return None
        cutoff = self.clock() - self.settings.lookback_seconds
        self._prune(samples, cutoff)
        points = list(samples)
        if len(points) < 2:
            return None
        if points[0].time < cutoff:
            first, second = points[:2]
            fraction = (cutoff - first.time) / (second.time - first.time)
            points[0] = WristSample(cutoff, interpolate(first.point, second.point, fraction))
        settings = self.settings.movement
        progress = AverageDistanceAccumulator(
            {"wrist": points[0].point}, WeightedDistance(settings.axis_weights, frame_aspect), settings,
        )
        for start, end in zip(points, points[1:]):
            progress.advance({"wrist": PathSegment(start.point, end.point)})
        if progress.distance < self.settings.activation_distance:
            return None
        return CommandModifier(
            self.settings.QUALIFIED_REPEAT_COUNT,
            self.settings.repeat_delay_ms / 1000,
            self.settings.delay_variance_ms / 1000,
        )
