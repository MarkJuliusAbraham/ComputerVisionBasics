"""One repeat budget per detected gesture, shared by its tracked fingertips."""

import time
from collections import deque
from dataclasses import dataclass, field, replace
from math import isfinite
from typing import TYPE_CHECKING

from .distance import AverageDistanceAccumulator, RepeatCrossing, WeightedDistance
from .shake import HandShakeDetector

if TYPE_CHECKING:
    from hand_tracking.backend.gestures.gesture_config import GestureDefinition


@dataclass
class RepeatInstance:
    definition: "GestureDefinition"
    progress: AverageDistanceAccumulator | None
    last_repeat_time: float
    scheduled: int = 0
    movement_scheduled: int = 0
    count: int = 0
    in_flight: bool = False
    pending: deque[RepeatCrossing] = field(default_factory=deque)
    shake: HandShakeDetector | None = None


class MovementRepeatController:
    def __init__(self, on_repeat, on_marker, *, clock=None):
        self.on_repeat = on_repeat
        self.on_marker = on_marker
        self.clock = clock if clock is not None else time.monotonic
        self._instance = None

    def clear(self):
        self._instance = None

    @property
    def remembers_shake_gesture(self):
        """The active instance owns the last triggered gesture and its budget."""
        return self._instance is not None and self._instance.shake is not None

    @property
    def remembers_gesture(self):
        return (self._instance is not None
                and self._instance.definition.repeat_settings.trigger in ("shake", "distance"))

    def interrupt_shake(self):
        """Discard partial motion and queued repeats, retaining the gesture/budget."""
        instance = self._instance
        if instance is not None and instance.shake is not None:
            instance.shake = HandShakeDetector(
                instance.definition.repeat_settings, instance.shake.aspect,
            )
            instance.pending.clear()
            instance.in_flight = False
            instance.scheduled = instance.count
            instance.last_repeat_time = self.clock()

    def interrupt_motion(self):
        """Keep the remembered command and distance remainder across interruptions."""
        if self.remembers_shake_gesture:
            self.interrupt_shake()
        elif self.remembers_gesture:
            instance = self._instance
            # Queued/in-flight commands are cancelled by the caller; retain
            # their earned distance so they can be scheduled after resuming.
            cancelled = len(instance.pending) + int(instance.in_flight)
            instance.movement_scheduled -= cancelled
            instance.scheduled = instance.count
            instance.pending.clear()
            instance.in_flight = False
            if instance.progress is not None:
                instance.progress.rebase()
            instance.last_repeat_time = self.clock()

    def start(self, definition, state, frame_aspect=1.0):
        self.clear()
        settings = definition.repeat_settings
        if not settings.max_repeats:
            return
        metric = WeightedDistance(settings.movement.axis_weights, frame_aspect)
        origins = {}
        for name in definition.tracking.fingers:
            finger = state.fingers.get(name)
            if finger is not None and all(isfinite(value) for value in finger.tip):
                origins[name] = tuple(finger.tip)
        progress = None
        if settings.trigger in ("tracking", "distance") and origins and len(origins) == len(definition.tracking.fingers):
            movement = settings.movement
            if settings.trigger == "distance":
                movement = replace(movement, initial_displacement=0, buffer_credit=0)
            progress = AverageDistanceAccumulator(origins, metric, movement)
        self._instance = RepeatInstance(definition, progress, self.clock())
        if settings.trigger == "shake":
            self._instance.shake = HandShakeDetector(settings, frame_aspect)
            self._instance.shake.observe(
                state.wrist, state.palm_size, self.clock(),
                {name: finger.tip for name, finger in state.fingers.items()},
            )

    def reserve_optimistic(self, requested):
        instance = self._instance
        if instance is None:
            return 0
        available = instance.definition.repeat_settings.max_repeats - instance.scheduled
        reserved = min(requested, available)
        instance.scheduled += reserved
        return reserved

    def optimistic_repeat_started(self):
        if self._instance is not None:
            self._instance.count += 1
            self._instance.last_repeat_time = self.clock()

    def observe(self, segments, state=None):
        instance = self._instance
        if instance is None:
            return
        settings = instance.definition.repeat_settings
        if instance.scheduled >= settings.max_repeats:
            self.update()
            return
        if instance.shake is not None:
            if instance.shake.observe(
                state.wrist if state is not None else None,
                state.palm_size if state is not None else None, self.clock(),
                {name: finger.tip for name, finger in state.fingers.items()} if state is not None else None,
            ):
                instance.pending.append(RepeatCrossing(
                    1.0, tuple((name, segment.end) for name, segment in segments.items()),
                ))
                instance.scheduled += 1
            self.update()
            return
        advance = instance.progress.advance(segments) if instance.progress is not None else None
        if advance is not None:
            while instance.scheduled < settings.max_repeats:
                target = (instance.movement_scheduled + 1) * settings.distance_threshold
                if advance.after < target:
                    break
                instance.pending.append(advance.crossing(target))
                instance.scheduled += 1
                instance.movement_scheduled += 1
        self.update()

    def update(self):
        instance = self._instance
        if instance is None or not instance.pending or instance.in_flight:
            return
        now = self.clock()
        if now - instance.last_repeat_time < instance.definition.repeat_settings.min_interval_seconds:
            return
        crossing = instance.pending.popleft()
        instance.in_flight = True
        self.on_repeat(
            instance.definition,
            on_start=lambda: self._repeat_started(instance, crossing),
        )

    def _repeat_started(self, instance, crossing):
        if self._instance is not instance:
            return
        instance.in_flight = False
        for finger, point in crossing.markers:
            self.on_marker(finger, point)
        instance.count += 1
        instance.last_repeat_time = self.clock()
