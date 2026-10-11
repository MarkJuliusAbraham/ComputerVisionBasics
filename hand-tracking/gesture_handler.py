import math
import time

from custom_overlay.invoker_overlay import InvokerOverlay
from gestures.detector import GestureState
from gestures.gesture_config import GestureConfig
from gestures.gesture_matcher import GestureMatcher
from gestures.gesture_detector import Pinching
from input.command_executor import CommandExecutor
from volume_controller import VolumeController


class GestureHandler:
    ENABLE_REPEAT = True

    # Horizontal-plane (X/Z) distance required between repeat triggers.
    X_REPEAT_THRESHOLD = 0.09

    # Z is a noisy model estimate, so it counts for less than X.
    # Set to 0 to get X-only behavior.
    Z_WEIGHT = 0.5

    # Minimum time between repeated taps.
    REPEAT_MIN_INTERVAL = 0.05

    # Maximum number of additional taps per gesture.
    MAX_REPEATS = 2

    # Horizontal-plane movement must be at least this fraction
    # of vertical movement to count.
    HORIZONTAL_BIAS = 0.4

    def __init__(self, invoker_overlay: InvokerOverlay, config=None):
        self.volume = VolumeController()
        self.invoker_overlay = invoker_overlay
        self.config = config or GestureConfig.load()
        self.matcher = GestureMatcher()
        self.definitions_by_id = {
            definition.id: definition for definition in self.config.definitions
        }
        self.command_executor = CommandExecutor(
            on_command=self.invoker_overlay.addCommand
        )

        self._pinching = False
        self._previous_y = 0.0

        self._input_locked = False

        # True while the hand is held closed.
        self._reset_active = False

        # Active gesture repeat state.
        self._active_gesture = None
        self._repeat_count = 0

        # Horizontal-plane distance accumulated since the last
        # repeat threshold was crossed.
        self._repeat_distance = 0.0

        # Thresholds crossed but waiting for the minimum interval.
        self._pending_repeats = 0

        # Time of the most recent repeat tap.
        self._last_repeat_time = None

        # Tracked fingertip position from the previous frame.
        self._previous_x = None
        self._previous_fingertip_y = None
        self._previous_z = None

    def handle(self, state: GestureState):
        # Reset always gets checked first.
        if self.matcher.matches(self.config.reset_match, state):
            self._reset_active = True
            self._input_locked = False
            self._clear_repeat_state()

            return None

        self._reset_active = False

        # While locked, only repeatable gestures can generate
        # additional inputs from movement.
        if self._input_locked:
            if (
                self.ENABLE_REPEAT
                and self._active_gesture is not None
                and self.definitions_by_id[self._active_gesture].repeat_fingers
            ):
                x, y, z = self._tracked_position(
                    state,
                    self._active_gesture,
                )
                self._handle_repeat(x, y, z)
                self._store_previous(x, y, z)

            return None

        definition = self.matcher.find_match(self.config.definitions, state)

        if definition is None:
            return None

        if self.ENABLE_REPEAT and definition.repeat_fingers:
            self._active_gesture = definition.id
            self._repeat_count = 0
            self._repeat_distance = 0.0
            self._pending_repeats = 0

            # The initial gesture establishes the starting point
            # for repeat timing and position.
            self._last_repeat_time = time.monotonic()
            self._store_previous(*self._tracked_position(state, definition.id))
        else:
            self._clear_repeat_state()

        self._press(definition)

        self._latch()

        return definition.id

    def _clear_repeat_state(self):
        self._active_gesture = None
        self._repeat_count = 0
        self._repeat_distance = 0.0
        self._pending_repeats = 0
        self._last_repeat_time = None
        self._previous_x = None
        self._previous_fingertip_y = None
        self._previous_z = None

    def _store_previous(self, x, y, z):
        self._previous_x = x
        self._previous_fingertip_y = y
        self._previous_z = z

    def _press(self, definition):
        """Execute the command sequence attached to a gesture definition."""
        self.command_executor.execute(definition.commands)

    def _handle_repeat(self, current_x, current_y, current_z):
        if self._active_gesture is None:
            return

        if (
            self._previous_x is None
            or self._previous_fingertip_y is None
            or self._previous_z is None
        ):
            return

        # Stop completely once the maximum number of repeats
        # has been reached.
        if self._repeat_count >= self.MAX_REPEATS:
            return

        # Movement since the previous frame.
        dx = current_x - self._previous_x
        dy = current_y - self._previous_fingertip_y
        dz = (current_z - self._previous_z) * self.Z_WEIGHT

        # Movement in the horizontal plane (X and Z together).
        horizontal = math.hypot(dx, dz)

        # Ignore movement that isn't sufficiently horizontal.
        if horizontal < self.HORIZONTAL_BIAS * abs(dy):
            return

        # Accumulate horizontal-plane movement.
        self._repeat_distance += horizontal

        # Convert crossed spatial thresholds into pending repeats.
        # A large frame-to-frame jump can cross more than one
        # threshold, but we don't immediately fire all of them.
        while (
            self._repeat_distance >= self.X_REPEAT_THRESHOLD
            and (
                self._repeat_count + self._pending_repeats
            ) < self.MAX_REPEATS
        ):
            self._repeat_distance -= self.X_REPEAT_THRESHOLD
            self._pending_repeats += 1

        # Nothing waiting to be fired.
        if self._pending_repeats <= 0:
            return

        now = time.monotonic()

        # Don't allow repeated taps to happen too close together.
        if self._last_repeat_time is not None:
            if now - self._last_repeat_time < self.REPEAT_MIN_INTERVAL:
                return

        # Fire exactly one pending repeat. It doesn't return through
        # handle(), so it reports itself directly.
        self._press(
            self.definitions_by_id[self._active_gesture],
        )

        self._repeat_count += 1
        self._pending_repeats -= 1

        self._last_repeat_time = now

    def _tracked_position(self, state, gesture):
        """Average x, y, z of the fingertips relevant to this gesture."""
        repeat_fingers = self.definitions_by_id[gesture].repeat_fingers
        tips = [state.fingers[name].tip for name in repeat_fingers]
        n = len(tips)

        return (
            sum(tip[0] for tip in tips) / n,
            sum(tip[1] for tip in tips) / n,
            # Tolerates (x, y) tips: z counts as 0 until they carry it.
            sum(tip[2] if len(tip) > 2 else 0.0 for tip in tips) / n,
        )

    def _latch(self):
        self._input_locked = True

    def _handle_pinching(self, gesture: Pinching):
        delta = self._previous_y - gesture.current_pos[1]

        sensitivity = 8.25

        self.volume.level += delta * sensitivity

        self._previous_y = gesture.current_pos[1]
