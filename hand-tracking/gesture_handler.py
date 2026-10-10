import math
import time

from custom_overlay.invoker_overlay import InvokerOverlay
from gestures.detector import GestureState
from gestures.finger_classifier import FingerPosition
from gestures.gesture_detector import Pinching
from gestures.palm_detector import PalmPosition
from input.input_simulator import InputSimulator
from volume_controller import VolumeController


class GestureHandler:
    ENABLE_REPEAT = True

    # Horizontal-plane (X/Z) distance required between repeat triggers.
    X_REPEAT_THRESHOLD = 0.03

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

    # Only these gestures can repeat through movement.
    REPEATABLE_GESTURES = {"q", "w", "e"}

    # Fingertips tracked for each repeatable gesture (the extended fingers).
    REPEAT_FINGERS = {
        "q": ("index", "middle"),
        "w": ("middle", "ring"),
        "e": ("index",),
    }

    def __init__(self, invoker_overlay: InvokerOverlay):
        self.volume = VolumeController()
        self.input_simulator = InputSimulator()
        self.invoker_overlay = invoker_overlay

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
        if self.handleReset(state):
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
                and self._active_gesture in self.REPEATABLE_GESTURES
            ):
                x, y, z = self._tracked_position(
                    state,
                    self._active_gesture,
                )
                self._handle_repeat(x, y, z)
                self._store_previous(x, y, z)

            return None

        result = self._detect_gesture(state)

        if result is None:
            return None

        # Only Q/W/E establish repeat tracking.
        if self.ENABLE_REPEAT and result in self.REPEATABLE_GESTURES:
            self._active_gesture = result
            self._repeat_count = 0
            self._repeat_distance = 0.0
            self._pending_repeats = 0

            # The initial gesture establishes the starting point
            # for repeat timing and position.
            self._last_repeat_time = time.monotonic()
            self._store_previous(*self._tracked_position(state, result))
        else:
            self._clear_repeat_state()

        # Initial input. The main loop reports it via addCommand,
        # so report=False here.
        self._press(result)

        self._latch()

        return result

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

    def _press(self, command, report=False):
        """
        Perform a button press.

        The initial gesture is reported by the main loop, so
        report=False is used for the initial press.

        Repeated presses don't return through handle(), so they
        pass report=True and are reported directly here.
        """
        self.input_simulator.tap(command)

        if report:
            self.invoker_overlay.addCommand(command)

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
            self._active_gesture,
            report=True,
        )

        self._repeat_count += 1
        self._pending_repeats -= 1

        self._last_repeat_time = now

    def _tracked_position(self, state, gesture):
        """Average x, y, z of the fingertips relevant to this gesture."""
        tips = [
            state.fingers[name].tip
            for name in self.REPEAT_FINGERS[gesture]
        ]
        n = len(tips)

        return (
            sum(tip[0] for tip in tips) / n,
            sum(tip[1] for tip in tips) / n,
            # Tolerates (x, y) tips: z counts as 0 until they carry it.
            sum(tip[2] if len(tip) > 2 else 0.0 for tip in tips) / n,
        )

    def _detect_gesture(self, state: GestureState):
        if self.handleR(state):
            return "r"

        if self.handleQ(state):
            return "q"

        if self.handleW(state):
            return "w"

        if self.handleE(state):
            return "e"

        if self.handleD(state):
            return "d"

        if self.handleF(state):
            return "f"

        return None

    def _latch(self):
        self._input_locked = True

    def handleQ(self, state: GestureState):
        return (
            state.palm == PalmPosition.NOT_FACING_CAMERA
            and state.fingers["index"].position == FingerPosition.STRAIGHT
            and state.fingers["middle"].position == FingerPosition.STRAIGHT
            and state.fingers["ring"].position == FingerPosition.CLOSED
            and state.fingers["pinky"].position == FingerPosition.CLOSED
        )

    def handleW(self, state: GestureState):
        return (
            state.palm == PalmPosition.NOT_FACING_CAMERA
            and state.fingers["index"].position != FingerPosition.STRAIGHT
            and state.fingers["middle"].position == FingerPosition.STRAIGHT
            and state.fingers["ring"].position == FingerPosition.STRAIGHT
            and state.fingers["pinky"].position != FingerPosition.STRAIGHT
        )

    def handleE(self, state: GestureState):
        return (
            state.palm == PalmPosition.NOT_FACING_CAMERA
            and state.fingers["index"].position == FingerPosition.STRAIGHT
            and state.fingers["middle"].position != FingerPosition.STRAIGHT
            and state.fingers["middle"].position != FingerPosition.PARTIAL
            and state.fingers["ring"].position != FingerPosition.STRAIGHT
            and state.fingers["pinky"].position != FingerPosition.STRAIGHT
        )

    def handleR(self, state: GestureState):
        positions = (
            state.fingers["index"].position,
            state.fingers["middle"].position,
            state.fingers["ring"].position,
            state.fingers["pinky"].position,
        )

        return (
            sum(p == FingerPosition.STRAIGHT for p in positions) >= 3
            and all(
                p in (FingerPosition.PARTIAL, FingerPosition.STRAIGHT)
                for p in positions
            )
        )

    def handleD(self, state: GestureState):
        return (
            state.palm == PalmPosition.FACING_CAMERA
            and state.fingers["index"].position == FingerPosition.STRAIGHT
            and state.fingers["middle"].position == FingerPosition.STRAIGHT
            and state.fingers["ring"].position != FingerPosition.STRAIGHT
            and state.fingers["pinky"].position != FingerPosition.STRAIGHT
        )

    def handleF(self, state: GestureState):
        return (
            state.palm == PalmPosition.FACING_CAMERA
            and state.fingers["index"].position != FingerPosition.STRAIGHT
            and state.fingers["middle"].position == FingerPosition.STRAIGHT
            and state.fingers["ring"].position == FingerPosition.STRAIGHT
            and state.fingers["pinky"].position == FingerPosition.STRAIGHT
        )

    def handleReset(self, state: GestureState):
        return (
            state.fingers["index"].position != FingerPosition.STRAIGHT
            and state.fingers["middle"].position != FingerPosition.STRAIGHT
            and state.fingers["ring"].position != FingerPosition.STRAIGHT
            and state.fingers["pinky"].position != FingerPosition.STRAIGHT
        )

    def _handle_pinching(self, gesture: Pinching):
        delta = self._previous_y - gesture.current_pos[1]

        sensitivity = 8.25

        self.volume.level += delta * sensitivity

        self._previous_y = gesture.current_pos[1]