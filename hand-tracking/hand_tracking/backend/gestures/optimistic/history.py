"""Bounded rolling wrist paths, measured with the same rules as fingertips.

Each detection's wrist is smoothed with a One Euro filter before it is
measured, so landmark jitter does not add up to false movement over the
lookback window. Optionally, movement is scaled by the apparent palm size so
the same real hand motion counts the same at any distance from the camera.
"""

import math
import time
from collections import deque
from dataclasses import dataclass

from hand_tracking.backend.gestures.repeating.distance import (
    AverageDistanceAccumulator,
    WeightedDistance,
    interpolate,
)
from hand_tracking.backend.gestures.tracking.path import PathSegment, Point
from hand_tracking.backend.input.command_modifier import CommandModifier

from .settings import OptimisticTrackingSettings
from .smoothing import OneEuroFilter


# Palm size changes slowly; smooth it heavily so the distance scale is steady.
PALM_SIZE_CUTOFF_HZ = 1.0


@dataclass(frozen=True)
class WristSample:
    time: float
    # Smoothed and, when enabled, scaled by hand size. Only the movement
    # between samples is meaningful, not the absolute position.
    point: Point


class WristTrack:
    """One hand's recent samples and the filter state that produced them."""

    def __init__(self, settings):
        self.samples = deque()
        self.raw = None         # Latest detection; cached results repeat it
        self.smoothed = None    # Latest filtered wrist position
        cutoff = settings.smoothing_min_cutoff_hz
        self.wrist_filter = OneEuroFilter(cutoff, settings.smoothing_beta) if cutoff else None
        self.palm_filter = OneEuroFilter(PALM_SIZE_CUTOFF_HZ, 0.0)

    def scale(self, settings, now, palm_size):
        """Movement multiplier, or None when the palm size is unusable."""
        if not settings.scale_with_hand_size:
            return 1.0
        if palm_size is None or not math.isfinite(palm_size) or palm_size <= 0:
            return None
        (size,) = self.palm_filter(now, (palm_size,))
        return settings.reference_palm_size / size

    def add(self, now, raw, smoothed, scale):
        if self.samples:
            # Integrate scaled movement so a changing scale never moves earlier samples.
            previous = self.samples[-1].point
            position = tuple(p + (new - old) * scale for p, new, old in zip(previous, smoothed, self.smoothed))
        else:
            position = smoothed
        self.raw, self.smoothed = raw, smoothed
        self.samples.append(WristSample(now, position))


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
        track = self._hands.get(hand)
        if track is not None and track.samples:
            track.samples = deque((track.samples[-1],))

    def record(self, hand, wrist, palm_size=None):
        """Add one detection; ``palm_size`` is a fraction of the frame width."""
        if wrist is None:
            self._hands.pop(hand, None)
            return
        if not self.settings.enabled:
            return
        point = tuple(float(value) for value in wrist)
        if len(point) != 3 or not all(math.isfinite(value) for value in point):
            self._hands.pop(hand, None)
            return
        track = self._hands.get(hand)
        # The frame loop runs faster than inference and sees each result
        # repeatedly. Count every detection once so the filter's timing holds.
        if track is not None and point == track.raw:
            return
        now = self.clock()
        if track is not None and track.samples:
            if now <= track.samples[-1].time:
                return
            if now - track.samples[-1].time > self.settings.lookback_seconds:
                track = None
        if track is None:
            track = self._hands[hand] = WristTrack(self.settings)
        scale = track.scale(self.settings, now, palm_size)
        if scale is None:
            self._hands.pop(hand, None)
            return
        smoothed = track.wrist_filter(now, point) if track.wrist_filter else point
        track.add(now, point, smoothed, scale)
        self._prune(track.samples, now - self.settings.lookback_seconds)

    @staticmethod
    def _prune(samples, cutoff):
        # Keep one sample before the boundary to interpolate the exact window.
        while len(samples) > 1 and samples[1].time <= cutoff:
            samples.popleft()

    def modifier_for(self, hand, frame_aspect=1.0):
        track = self._hands.get(hand)
        samples = track.samples if track is not None else None
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
