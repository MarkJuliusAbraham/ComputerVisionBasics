import math
import time

from custom_overlay.invoker_overlay import InvokerOverlay
from gestures.detector import GestureState
from gestures.gesture_config import GestureConfig
from gestures.gesture_matcher import AmbiguousGestureError, GestureMatcher
from gestures.gesture_validation import GestureCriteriaValidator
from gestures.profile_manager import GestureProfileManager
from input.command_executor import CommandExecutor


class GestureHandler:
    ENABLE_REPEAT = True
    MAX_PATH_POINTS = 2048

    def __init__(self, invoker_overlay: InvokerOverlay, config=None, *, criteria_validator=None):
        self.invoker_overlay = invoker_overlay
        if config is None:
            config = GestureConfig.load(
                GestureProfileManager().active_profile
            )
        self.criteria_validator = (
            criteria_validator if criteria_validator is not None else GestureCriteriaValidator()
        )
        self._set_config(config)
        self.matcher = GestureMatcher()
        self.command_executor = CommandExecutor(
            on_command=self.invoker_overlay.addCommand
        )

        self._input_locked = False

        # True while the hand is held closed.
        self._reset_active = False

        # Active gesture repeat state.
        self._active_gesture = None
        self._repeat_count = 0

        # Traveled fingertip path length since the last repeat threshold.
        self._repeat_distance = 0.0
        self._repeat_origin = None
        self._repeat_armed = False

        # Path positions where thresholds were crossed, waiting for interval.
        self._pending_repeats = []

        # Time of the most recent repeat tap.
        self._last_repeat_time = None

        self._active_repeat_hand = None
        self._active_path_finger = None
        self._active_path_hand = None
        self._frame_aspect = 1.0
        self._path_points = []
        self._repeat_markers = []
        self._completed_path = None

    def configure(self, config):
        """Replace the gesture map and clear any active latch/repeat state."""
        self.command_executor.clear()
        self._set_config(config)
        self._input_locked = False
        self._reset_active = False
        self._clear_repeat_state()
        self._clear_path()

    def _set_config(self, config):
        self.config = config
        self.definitions_by_id = {definition.id: definition for definition in config.definitions}
        report = self.criteria_validator.validate(
            {definition.id: definition.match for definition in config.definitions}, config.reset_match,
        )
        invalid_ids = report.invalid_ids
        self._valid_definitions = tuple(
            definition for definition in config.definitions if definition.id not in invalid_ids
        )

    def update(self, allow_repeats=True):
        """Advance delayed command actions from the application event loop."""
        self.command_executor.update()
        if allow_repeats:
            self._fire_pending_repeat()

    def close(self):
        self.command_executor.clear()
        self._clear_path()

    def suspend(self):
        """Release input and cancel repeats while preserving the completed drawing."""
        self.command_executor.clear()
        self._finish_path()
        self._clear_repeat_state()
        self._input_locked = False
        self._reset_active = False

    @property
    def drawing_path(self):
        """Return fingertip, path points, and repeat marker positions."""
        if self._path_points and self._active_path_finger:
            return (
                self._active_path_finger, tuple(self._path_points),
                tuple(self._repeat_markers),
            )
        return self._completed_path

    def handle(
        self, state: GestureState, handedness=None, frame_size=None,
        invoke_commands=True,
    ):
        """Return the current gesture definition, optionally invoking its commands."""
        if invoke_commands and frame_size and frame_size[0]:
            self._frame_aspect = frame_size[1] / frame_size[0]
        # Reset always gets checked first.
        if self.matcher.matches(self.config.reset_match, state):
            if not invoke_commands:
                return None
            self.command_executor.clear()
            self._reset_active = True
            self._input_locked = False
            self._clear_repeat_state()
            self._clear_path()

            return None

        try:
            definition = self.matcher.find_match(self._valid_definitions, state)
        except AmbiguousGestureError:
            # Different criteria can still match the same particular hand.
            # Await an unambiguous hand state without stopping the UI callback.
            definition = None
        if not invoke_commands:
            return definition

        self._reset_active = False

        # While locked, only repeatable gestures can generate
        # additional inputs from movement.
        if self._input_locked:
            path_segment = None
            if self._active_path_hand in (None, handedness):
                path_segment = self._append_path_point(state)
            if (
                self.ENABLE_REPEAT
                and self._active_gesture is not None
                and self.definitions_by_id[self._active_gesture].repeat_fingers
                and self._active_repeat_hand in (None, handedness)
                and path_segment is not None
            ):
                self._handle_repeat(
                    path_segment[0], path_segment[1], self._frame_aspect
                )

            return definition

        if definition is None:
            return None

        self._start_path(definition, state, handedness)
        if (
            self.ENABLE_REPEAT
            and definition.repeat_fingers
            and self._active_path_finger is not None
        ):
            self._active_gesture = definition.id
            self._active_repeat_hand = handedness
            self._repeat_count = 0
            self._repeat_distance = 0.0
            self._repeat_origin = self._path_points[0]
            self._repeat_armed = False
            self._pending_repeats = []

            # The initial gesture establishes the starting point
            # for repeat timing and position.
            self._last_repeat_time = time.monotonic()
        else:
            self._clear_repeat_state()

        self._press(definition)

        self._latch()

        return definition

    def _clear_repeat_state(self):
        self._active_gesture = None
        self._active_repeat_hand = None
        self._repeat_count = 0
        self._repeat_distance = 0.0
        self._repeat_origin = None
        self._repeat_armed = False
        self._pending_repeats = []
        self._last_repeat_time = None

    def _start_path(self, definition, state, handedness):
        self._completed_path = None
        self._path_points = []
        self._repeat_markers = []
        self._active_path_finger = definition.tracked_finger
        if self._active_path_finger in state.fingers:
            self._active_path_hand = handedness
            self._append_path_point(state)
        else:
            self._active_path_finger = None
            self._active_path_hand = None

    def _append_path_point(self, state):
        if self._active_path_finger not in state.fingers:
            return None
        tip = state.fingers[self._active_path_finger].tip
        point = (float(tip[0]), float(tip[1]))
        if not self._path_points:
            self._path_points.append(point)
            return None
        previous = self._path_points[-1]
        if point == previous:
            return None
        self._path_points.append(point)
        if len(self._path_points) > self.MAX_PATH_POINTS:
            self._path_points = self._path_points[::2]
            if self._path_points[-1] != point:
                self._path_points.append(point)
        return previous, point

    def _finish_path(self):
        if self._path_points and self._active_path_finger:
            self._completed_path = (
                self._active_path_finger,
                tuple(self._path_points),
                tuple(self._repeat_markers),
            )
        self._path_points = []
        self._repeat_markers = []
        self._active_path_finger = None
        self._active_path_hand = None

    def _clear_path(self):
        self._path_points = []
        self._repeat_markers = []
        self._completed_path = None
        self._active_path_finger = None
        self._active_path_hand = None

    def _press(self, definition):
        """Execute the command sequence attached to a gesture definition."""
        self.command_executor.execute(definition.commands)

    def _handle_repeat(self, segment_start, segment_end, frame_aspect):
        if self._active_gesture is None:
            return

        # Stop completely once the maximum number of repeats
        # has been reached.
        settings = self.config.repeat_settings
        if self._repeat_count >= settings.max_repeats:
            return

        start_x, start_y = segment_start
        end_x, end_y = segment_end
        if not self._repeat_armed:
            if settings.initial_displacement <= 0:
                self._repeat_armed = True
            else:
                origin_x, origin_y = self._repeat_origin
                origin_metric = (origin_x, origin_y * frame_aspect)
                start_metric = (start_x, start_y * frame_aspect)
                end_metric = (end_x, end_y * frame_aspect)
                displacement = math.hypot(
                    end_metric[0] - origin_metric[0],
                    end_metric[1] - origin_metric[1],
                )
                if displacement < settings.initial_displacement:
                    return

                # Find where this segment first crosses the displacement
                # radius. The movement up to that point is the dead zone.
                dx = end_metric[0] - start_metric[0]
                dy = end_metric[1] - start_metric[1]
                offset_x = start_metric[0] - origin_metric[0]
                offset_y = start_metric[1] - origin_metric[1]
                a = dx * dx + dy * dy
                b = 2 * (offset_x * dx + offset_y * dy)
                c = (
                    offset_x * offset_x + offset_y * offset_y
                    - settings.initial_displacement ** 2
                )
                discriminant = max(0.0, b * b - 4 * a * c)
                fraction = max(
                    0.0,
                    min(1.0, (-b + math.sqrt(discriminant)) / (2 * a)),
                )
                start_x += (end_x - start_x) * fraction
                start_y += (end_y - start_y) * fraction
                self._repeat_armed = True

        segment_length = math.hypot(
            end_x - start_x, (end_y - start_y) * frame_aspect
        )
        if segment_length <= 0:
            return

        # Measure the full 2D polyline length traced by the same fingertip
        # shown in the overlay. Interpolate threshold points within a frame
        # segment so repeat markers sit directly on the drawn path.
        distance_in_segment = segment_length
        distance_consumed = 0.0
        while (
            self._repeat_distance + distance_in_segment
            >= settings.distance_threshold
            and (self._repeat_count + len(self._pending_repeats))
            < settings.max_repeats
        ):
            distance_to_crossing = settings.distance_threshold - self._repeat_distance
            distance_consumed += distance_to_crossing
            fraction = distance_consumed / segment_length
            crossing = (
                start_x + (end_x - start_x) * fraction,
                start_y + (end_y - start_y) * fraction,
            )
            self._pending_repeats.append(crossing)
            distance_in_segment -= distance_to_crossing
            self._repeat_distance = 0.0
        self._repeat_distance += distance_in_segment

        self._fire_pending_repeat()

    def _fire_pending_repeat(self):
        """Fire due repeats even when the fingertip has stopped moving."""
        if self._active_gesture is None:
            return
        settings = self.config.repeat_settings
        if not self._pending_repeats:
            return

        now = time.monotonic()

        # Don't allow repeated taps to happen too close together.
        if self._last_repeat_time is not None:
            if now - self._last_repeat_time < settings.min_interval_seconds:
                return

        # Fire exactly one pending repeat. It doesn't return through
        # handle(), so it reports itself directly.
        self._press(
            self.definitions_by_id[self._active_gesture],
        )
        self._repeat_markers.append(self._pending_repeats.pop(0))

        self._repeat_count += 1

        self._last_repeat_time = now

    def _latch(self):
        self._input_locked = True
