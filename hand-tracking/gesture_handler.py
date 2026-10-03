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

    # Horizontal distance required between repeat triggers.
    X_REPEAT_THRESHOLD = 0.03

    # Minimum time between repeated taps.
    # This prevents multiple repeats from firing back-to-back
    # when a frame crosses multiple distance thresholds.
    REPEAT_MIN_INTERVAL = 0.05

    # Maximum number of additional taps per gesture.
    MAX_REPEATS = 2

    # Horizontal movement must be this many times larger
    # than vertical movement to count as horizontal.
    HORIZONTAL_BIAS = 0.4

    # Only these gestures can repeat through horizontal movement.
    REPEATABLE_GESTURES = {"q", "w", "e"}

    def __init__(self, invoker_overlay: InvokerOverlay):
        self.volume = VolumeController()
        self.input_simulator = InputSimulator()
        self.invoker_overlay = invoker_overlay

        self._pinching = False
        self._previous_y = 0.0

        self._input_locked = False

        # Active gesture repeat state.
        self._active_gesture = None
        self._repeat_count = 0

        # Horizontal distance accumulated since the last
        # repeat threshold was crossed.
        self._repeat_distance = 0.0

        # Number of spatial repeat thresholds that have been
        # crossed but are waiting for the minimum time interval.
        self._pending_repeats = 0

        # Time of the most recent repeat tap.
        self._last_repeat_time = None

        # Continuously tracked fingertip position.
        self._previous_x = None
        self._previous_fingertip_y = None

    def handle(self, state: GestureState):
        current_x, current_y = (
            self._average_fingertip_position(state)
        )

        # Reset always gets checked first.
        if self.handleReset(state):
            self._input_locked = False

            self._active_gesture = None
            self._repeat_count = 0
            self._repeat_distance = 0.0
            self._pending_repeats = 0
            self._last_repeat_time = None

            self._previous_x = current_x
            self._previous_fingertip_y = current_y

            return None

        # While locked, only repeatable gestures can generate
        # additional inputs from horizontal movement.
        if self._input_locked:
            if (
                self.ENABLE_REPEAT
                and self._active_gesture
                in self.REPEATABLE_GESTURES
            ):
                self._handle_repeat(
                    current_x,
                    current_y,
                )

            self._previous_x = current_x
            self._previous_fingertip_y = current_y

            return None

        result = self._detect_gesture(state)

        if result is None:
            self._previous_x = current_x
            self._previous_fingertip_y = current_y

            return None

        # Only Q/W/E establish repeat tracking.
        if (
            self.ENABLE_REPEAT
            and result in self.REPEATABLE_GESTURES
        ):
            self._active_gesture = result
            self._repeat_count = 0
            self._repeat_distance = 0.0
            self._pending_repeats = 0

            # The initial gesture establishes the starting point
            # for repeat timing.
            self._last_repeat_time = time.monotonic()
        else:
            self._active_gesture = None
            self._repeat_count = 0
            self._repeat_distance = 0.0
            self._pending_repeats = 0
            self._last_repeat_time = None

        # Initial input.
        #
        # Do NOT report it here. The main loop already does:
        #
        #     if result is not None:
        #         self.invoker_overlay.addCommand(result)
        #
        self._press(result)

        self._latch()

        self._previous_x = current_x
        self._previous_fingertip_y = current_y

        return result

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

    def _handle_repeat(self, current_x, current_y):
        if self._active_gesture is None:
            return

        if self._previous_x is None:
            return

        if self._previous_fingertip_y is None:
            return

        # Stop completely once the maximum number of repeats
        # has been reached.
        if self._repeat_count >= self.MAX_REPEATS:
            return

        # Movement since the previous frame.
        dx = current_x - self._previous_x
        dy = current_y - self._previous_fingertip_y

        # Ignore movement that isn't sufficiently horizontal.
        if abs(dx) < self.HORIZONTAL_BIAS * abs(dy):
            return

        # Accumulate horizontal movement.
        self._repeat_distance += abs(dx)

        # Convert crossed spatial thresholds into pending repeats.
        #
        # A large frame-to-frame jump can cross more than one
        # threshold, but we don't immediately fire all of them.
        while (
            self._repeat_distance >= self.X_REPEAT_THRESHOLD
            and (
                self._repeat_count
                + self._pending_repeats
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
            elapsed = now - self._last_repeat_time

            if elapsed < self.REPEAT_MIN_INTERVAL:
                return

        # Fire exactly one pending repeat.
        #
        # Unlike the initial command, this command does not
        # return through handle(), so it reports itself directly.
        self._press(
            self._active_gesture,
            report=True,
        )

        self._repeat_count += 1
        self._pending_repeats -= 1

        self._last_repeat_time = now

    def _average_fingertip_position(self, state):
        tips = [
            state.fingers["index"].tip,
            state.fingers["middle"].tip,
            state.fingers["ring"].tip,
            state.fingers["pinky"].tip,
        ]

        average_x = sum(
            tip[0] for tip in tips
        ) / len(tips)

        average_y = sum(
            tip[1] for tip in tips
        ) / len(tips)

        return average_x, average_y

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
            and state.fingers["index"].position
            == FingerPosition.STRAIGHT
            and state.fingers["middle"].position
            == FingerPosition.STRAIGHT
            and state.fingers["ring"].position
            == FingerPosition.CLOSED
            and state.fingers["pinky"].position
            == FingerPosition.CLOSED
        )

    def handleW(self, state: GestureState):
        return (
            state.palm == PalmPosition.NOT_FACING_CAMERA
            and state.fingers["index"].position
            != FingerPosition.STRAIGHT
            and state.fingers["middle"].position
            == FingerPosition.STRAIGHT
            and state.fingers["ring"].position
            == FingerPosition.STRAIGHT
            and state.fingers["pinky"].position
            != FingerPosition.STRAIGHT
        )

    def handleE(self, state: GestureState):
        return (
            state.palm == PalmPosition.NOT_FACING_CAMERA
            and state.fingers["index"].position
            == FingerPosition.STRAIGHT
            and state.fingers["middle"].position
            != FingerPosition.STRAIGHT
            and state.fingers["middle"].position
            != FingerPosition.PARTIAL
            and state.fingers["ring"].position
            != FingerPosition.STRAIGHT
            and state.fingers["pinky"].position
            != FingerPosition.STRAIGHT
        )

    def handleR(self, state: GestureState):
        positions = (
            state.fingers["index"].position,
            state.fingers["middle"].position,
            state.fingers["ring"].position,
            state.fingers["pinky"].position,
        )

        return (
            sum(
                position == FingerPosition.STRAIGHT
                for position in positions
            ) >= 3
            and all(
                position
                in (
                    FingerPosition.PARTIAL,
                    FingerPosition.STRAIGHT,
                )
                for position in positions
            )
        )

    def handleD(self, state: GestureState):
        return (
            state.palm == PalmPosition.FACING_CAMERA
            and state.fingers["index"].position
            == FingerPosition.STRAIGHT
            and state.fingers["middle"].position
            == FingerPosition.STRAIGHT
            and state.fingers["ring"].position
            != FingerPosition.STRAIGHT
            and state.fingers["pinky"].position
            != FingerPosition.STRAIGHT
        )

    def handleF(self, state: GestureState):
        return (
            state.palm == PalmPosition.FACING_CAMERA
            and state.fingers["index"].position
            != FingerPosition.STRAIGHT
            and state.fingers["middle"].position
            == FingerPosition.STRAIGHT
            and state.fingers["ring"].position
            == FingerPosition.STRAIGHT
            and state.fingers["pinky"].position
            == FingerPosition.STRAIGHT
        )

    def handleReset(self, state: GestureState):
        return (
            state.fingers["index"].position
            != FingerPosition.STRAIGHT
            and state.fingers["middle"].position
            != FingerPosition.STRAIGHT
            and state.fingers["ring"].position
            != FingerPosition.STRAIGHT
            and state.fingers["pinky"].position
            != FingerPosition.STRAIGHT
        )

    def _handle_pinching(self, gesture: Pinching):
        delta = self._previous_y - gesture.current_pos[1]

        sensitivity = 8.25

        self.volume.level += delta * sensitivity

        self._previous_y = gesture.current_pos[1]
