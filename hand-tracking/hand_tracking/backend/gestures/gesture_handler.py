from hand_tracking.backend.gestures.detector import GestureState
from hand_tracking.backend.gestures.gesture_config import GestureConfig
from hand_tracking.backend.gestures.gesture_matcher import AmbiguousGestureError, GestureMatcher
from hand_tracking.backend.gestures.gesture_validation import GestureCriteriaValidator
from hand_tracking.backend.gestures.profile_manager import GestureProfileManager
from hand_tracking.backend.gestures.optimistic.history import WristMovementHistory
from hand_tracking.backend.gestures.repeating.controller import MovementRepeatController
from hand_tracking.backend.gestures.tracking.tracker import GesturePathTracker
from hand_tracking.backend.input.command_executor import CommandExecutor
from hand_tracking.backend.input.command_modifier import CommandModifier
from hand_tracking.backend.gestures.settling_gate import FingerSettlingGate
import time


class GestureHandler:
    def __init__(
        self, config=None, *, on_command=None,
        criteria_validator=None, path_tracker=None, repeat_controller=None, wrist_history=None,
    ):
        if config is None:
            config = GestureConfig.load(GestureProfileManager().active_profile)
        self.criteria_validator = (
            criteria_validator if criteria_validator is not None else GestureCriteriaValidator()
        )
        self._set_config(config)
        self.matcher = GestureMatcher()
        self.command_executor = CommandExecutor(on_command=on_command)
        self.path_tracker = path_tracker if path_tracker is not None else GesturePathTracker()
        self.repeat_controller = (
            repeat_controller if repeat_controller is not None
            else MovementRepeatController(self._press, self.path_tracker.mark_repeat)
        )
        self.wrist_history = wrist_history if wrist_history is not None else WristMovementHistory()
        self._input_locked = False
        self._frame_aspect = 1.0
        self.settling_gate = FingerSettlingGate()

    def _set_config(self, config):
        self.config = config
        report = config.validation_report(self.criteria_validator)
        self._valid_definitions = tuple(
            definition for definition in config.definitions if definition.id not in report.invalid_ids
        )

    def _cancel_input(self, *, keep_drawing=False, keep_wrist_history=False, keep_shake=False):
        """Stop queued commands and repeats and re-arm gesture input."""
        self.command_executor.clear()
        self.settling_gate.reset()
        remembering = keep_shake and self.repeat_controller.remembers_gesture
        if remembering:
            self.repeat_controller.interrupt_motion()
        else:
            self.repeat_controller.clear()
        if remembering:
            pass  # Retain the owning hand/path so only it can resume shaking.
        elif keep_drawing:
            self.path_tracker.finish()
        else:
            self.path_tracker.clear()
        if not keep_wrist_history:
            self.wrist_history.clear()
        self._input_locked = remembering

    def configure(self, config):
        """Replace mappings and clear the active drawing and command instance."""
        self._cancel_input()
        self._set_config(config)

    def configure_optimistic(self, settings):
        if settings != self.wrist_history.settings:
            self.suspend()
            self.wrist_history.configure(settings)

    def configure_settling(self, settings):
        self.settling_gate.configure(settings.finger_settling_enabled,
                                     settings.finger_settling_max_speed)

    def update(self, allow_repeats=True):
        self.command_executor.update()
        if allow_repeats:
            self.repeat_controller.update()

    def close(self):
        self._cancel_input()

    def suspend(self):
        """Cancel input and repeats while preserving the completed drawing."""
        self._cancel_input(keep_drawing=True, keep_shake=True)

    @property
    def drawing_paths(self):
        return self.path_tracker.drawing_paths

    def finish_frame(self, present_hands, *, invoke_commands=True):
        self.wrist_history.finish_frame(present_hands)
        self.settling_gate.finish_frame(present_hands)
        if self.repeat_controller.remembers_gesture:
            if self.path_tracker.handedness not in present_hands:
                self.command_executor.clear()
                self.repeat_controller.interrupt_motion()
            return
        if invoke_commands and self.path_tracker.finish_missing_hand(present_hands):
            self.repeat_controller.clear()

    def handle(
        self, state: GestureState, handedness=None, frame_size=None,
        invoke_commands=True, sample_time=None,
    ):
        """Report the matched gesture independently of its command latch."""
        if invoke_commands and frame_size and frame_size[0]:
            self._frame_aspect = frame_size[1] / frame_size[0]
        self.wrist_history.record(handedness, state.wrist, state.palm_size)
        if self.matcher.matches(self.config.reset_match, state):
            if invoke_commands:
                # Wrist history remains continuous across gesture resets.
                # The lookback window decides which earlier motion qualifies.
                self._cancel_input(keep_wrist_history=True)
            return None

        try:
            definition = self.matcher.find_match(self._valid_definitions, state)
        except AmbiguousGestureError:
            definition = None
        if not invoke_commands:
            self.settling_gate.reset()
            return definition

        if self._input_locked:
            if self.path_tracker.owns_hand(handedness):
                if self.repeat_controller.remembers_gesture:
                    # Distance and shake repeat the last invoked gesture even when its
                    # finger pose stops matching. Ownership stays with this hand.
                    self.repeat_controller.observe(self.path_tracker.append(state), state)
                elif definition is None or definition.id != self.path_tracker.gesture_id:
                    self.path_tracker.finish()
                    self.repeat_controller.clear()
                else:
                    self.repeat_controller.observe(self.path_tracker.append(state), state)
            return definition

        ready = self.settling_gate.allows(
            state, handedness, definition, self._valid_definitions,
            sample_time if sample_time is not None else time.monotonic(),
        )
        if definition is None or not ready:
            return definition
        self.path_tracker.start(definition, state, handedness)
        self.repeat_controller.start(definition, state, self._frame_aspect)
        modifier = (
            self.wrist_history.modifier_for(handedness, self._frame_aspect)
            if (definition.use_optimistic_tracking and definition.repeat_settings.max_repeats
                and definition.repeat_settings.trigger == "tracking") else None
        )
        if modifier is not None:
            allowed = self.repeat_controller.reserve_optimistic(modifier.repeat_count)
            modifier = CommandModifier(
                allowed, modifier.delay_seconds, modifier.delay_variance_seconds,
            ) if allowed else None
            if modifier is not None:
                self.wrist_history.consume(handedness)
        self._press(
            definition, modifier=modifier,
            on_repeat=lambda: self._optimistic_repeat_started(definition.id),
        )
        self._input_locked = True
        return definition

    def _optimistic_repeat_started(self, gesture_id):
        self.repeat_controller.optimistic_repeat_started()
        self.path_tracker.mark_current_repeat(gesture_id)

    def _press(self, definition, *, modifier=None, on_start=None, on_repeat=None):
        self.command_executor.execute(
            definition.commands, modifier=modifier, on_start=on_start, on_repeat=on_repeat,
        )
