import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from gestures.finger_classifier import FINGER_POSITIONS
from gestures.hand_landmarks import FINGER_NAMES
from gestures.palm_detector import PalmPosition
from gestures.gesture_validation import GestureCriteriaValidator
from gestures.repeating.settings import RepeatSettings
from gestures.tracking.settings import GestureTrackingSettings
from json_storage import write_json_atomic


DEFAULT_GESTURE_PROFILE_DIR = Path(__file__).resolve().parents[1] / "gesture_profiles"
DEFAULT_GESTURE_CONFIG = DEFAULT_GESTURE_PROFILE_DIR / "invoker_profile.json"
DEFAULT_GESTURE_TEMPLATE = Path(__file__).with_name("default_gesture_profile.json")
PALM_POSITIONS = {position.value for position in PalmPosition}


@dataclass(frozen=True)
class GestureMatch:
    palm: str | None
    fingers: dict[str, frozenset[str]]

    def to_dict(self):
        result = {name: sorted(positions) for name, positions in self.fingers.items()}
        value = {"fingers": result}
        if self.palm is not None:
            value["palm"] = self.palm
        return value

    @classmethod
    def from_dict(cls, value, location):
        if not isinstance(value, dict):
            raise ValueError(f"{location} must be an object")
        palm = value.get("palm")
        if palm is not None and (
            not isinstance(palm, str) or palm not in PALM_POSITIONS
        ):
            raise ValueError(f"{location}.palm must be one of {sorted(PALM_POSITIONS)}")
        raw_fingers = value.get("fingers", {})
        if not isinstance(raw_fingers, dict):
            raise ValueError(f"{location}.fingers must be an object")

        fingers = {}
        for name, positions in raw_fingers.items():
            if name not in FINGER_NAMES:
                raise ValueError(f"Unknown finger {name!r} in {location}")
            if not isinstance(positions, list) or not positions:
                raise ValueError(f"{location}.fingers.{name} must be a non-empty list")
            if any(not isinstance(position, str) for position in positions):
                raise ValueError(f"{location}.fingers.{name} values must be strings")
            invalid = set(positions) - FINGER_POSITIONS
            if invalid:
                raise ValueError(
                    f"Invalid positions for {name} in {location}: {sorted(invalid)}"
                )
            fingers[name] = frozenset(positions)

        if palm is None and not fingers:
            raise ValueError(f"{location} must constrain palm or at least one finger")
        return cls(palm=palm, fingers=fingers)


@dataclass(frozen=True)
class CommandStep:
    type: str
    value: str

    def to_dict(self):
        return {"type": self.type, "value": self.value}


@dataclass(frozen=True)
class CommandSequence:
    steps: tuple[CommandStep, ...]
    delay_ms_between_steps: int = 0

    def to_dict(self):
        return {
            "steps": [step.to_dict() for step in self.steps],
            "delay_ms_between_steps": self.delay_ms_between_steps,
        }

    @classmethod
    def from_dict(cls, value, location):
        if not isinstance(value, dict):
            raise ValueError(f"{location} must be an object")
        raw_steps = value.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ValueError(f"{location}.steps must be a non-empty list")
        steps = []
        for index, raw in enumerate(raw_steps):
            if not isinstance(raw, dict) or raw.get("type") != "key_tap":
                raise ValueError(
                    f"{location}.steps[{index}].type must currently be 'key_tap'"
                )
            command = raw.get("value")
            if not isinstance(command, str) or len(command) != 1:
                raise ValueError(
                    f"{location}.steps[{index}].value must be a single character"
                )
            steps.append(CommandStep(type="key_tap", value=command))

        delay = value.get("delay_ms_between_steps", 0)
        if not isinstance(delay, int) or isinstance(delay, bool) or delay < 0:
            raise ValueError(f"{location}.delay_ms_between_steps must be >= 0")
        return cls(tuple(steps), delay)


@dataclass(frozen=True)
class GestureDefinition:
    id: str
    name: str
    match: GestureMatch
    commands: CommandSequence
    tracking: GestureTrackingSettings = GestureTrackingSettings()
    repeat_settings: RepeatSettings = RepeatSettings()
    use_optimistic_tracking: bool = True

    def to_dict(self):
        result = {
            "id": self.id,
            "name": self.name,
            "match": self.match.to_dict(),
            "commands": self.commands.to_dict(),
            "tracking": self.tracking.to_dict(),
            "repeat_settings": self.repeat_settings.to_dict(),
            "use_optimistic_tracking": self.use_optimistic_tracking,
        }
        return result


@dataclass(frozen=True)
class GestureConfig:
    definitions: tuple[GestureDefinition, ...]
    reset_match: GestureMatch
    repeat_settings: RepeatSettings = RepeatSettings()

    @property
    def criteria(self):
        """Each gesture's hand criteria, keyed by gesture id."""
        return {definition.id: definition.match for definition in self.definitions}

    def validation_report(self, validator=None):
        validator = validator if validator is not None else GestureCriteriaValidator()
        return validator.validate(self.criteria, self.reset_match)

    def to_dict(self):
        return {
            "version": 1,
            "reset_match": self.reset_match.to_dict(),
            "repeat_settings": self.repeat_settings.to_dict(),
            "gestures": [definition.to_dict() for definition in self.definitions],
        }

    def save(self, path=DEFAULT_GESTURE_CONFIG, *, allow_conflicts=False):
        """Validate, write, and return the profile exactly as it will load.

        The same parser used at startup checks commands, reset criteria, and
        repeat settings before the existing profile is replaced.
        """
        data = self.to_dict()
        validated = self.from_dict(data, allow_conflicts=allow_conflicts)
        write_json_atomic(path, data)
        return validated

    @classmethod
    def load(cls, path=DEFAULT_GESTURE_CONFIG):
        if Path(path) == DEFAULT_GESTURE_CONFIG and not DEFAULT_GESTURE_CONFIG.exists():
            ensure_default_gesture_profile()
        try:
            with open(path, encoding="utf-8") as file:
                raw = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Could not load gesture config {path}: {error}") from error

        # Keep structurally valid profiles available for inspection and repair.
        # Their conflict report determines which gestures can invoke commands.
        return cls.from_dict(raw, allow_conflicts=True)

    @classmethod
    def from_dict(cls, raw, *, allow_conflicts=False):
        """Validate profile data consistently for loading and saving."""

        if not isinstance(raw, dict) or raw.get("version") != 1:
            raise ValueError("Gesture config must be an object with version 1")
        raw_definitions = raw.get("gestures")
        if not isinstance(raw_definitions, list) or not raw_definitions:
            raise ValueError("Gesture config must define at least one gesture")

        repeat_defaults = RepeatSettings.from_dict(raw.get("repeat_settings"))
        definitions = []
        ids = set()
        for index, item in enumerate(raw_definitions):
            location = f"gestures[{index}]"
            if not isinstance(item, dict):
                raise ValueError(f"{location} must be an object")
            gesture_id = item.get("id")
            if not isinstance(gesture_id, str) or not gesture_id.strip():
                raise ValueError(f"{location}.id must be a non-empty string")
            if gesture_id in ids:
                raise ValueError(f"Duplicate gesture id {gesture_id!r}")
            ids.add(gesture_id)
            name = item.get("name", gesture_id)
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"{location}.name must be a non-empty string")

            repeat_fingers = item.get("repeat_fingers", [])
            if (
                not isinstance(repeat_fingers, list)
                or any(not isinstance(name, str) for name in repeat_fingers)
                or any(name not in FINGER_NAMES for name in repeat_fingers)
            ):
                raise ValueError(f"{location}.repeat_fingers contains an unknown finger")
            if len(set(repeat_fingers)) != len(repeat_fingers):
                raise ValueError(f"{location}.repeat_fingers cannot contain duplicates")

            tracking = GestureTrackingSettings.from_gesture(item, location, repeat_fingers)
            use_optimistic = item.get("use_optimistic_tracking", True)
            if not isinstance(use_optimistic, bool):
                raise ValueError(f"{location}.use_optimistic_tracking must be a boolean")

            definitions.append(GestureDefinition(
                id=gesture_id,
                name=name,
                match=GestureMatch.from_dict(item.get("match"), f"{location}.match"),
                commands=CommandSequence.from_dict(
                    item.get("commands"), f"{location}.commands"
                ),
                tracking=tracking,
                use_optimistic_tracking=use_optimistic,
                repeat_settings=RepeatSettings.from_dict(
                    item.get("repeat_settings", repeat_defaults.to_dict())
                ),
            ))

        reset_match = GestureMatch.from_dict(raw.get("reset_match"), "reset_match")
        if not allow_conflicts:
            cls._validate_no_conflicts(definitions, reset_match)
        return cls(
            tuple(definitions), reset_match,
            repeat_defaults,
        )

    @staticmethod
    def _validate_no_conflicts(definitions, reset_match):
        report = GestureConfig(tuple(definitions), reset_match).validation_report()
        if report.conflicts:
            gesture_id = next(iter(report.conflicts))
            names = {definition.id: definition.name for definition in definitions}
            raise ValueError(
                f'Gesture "{names[gesture_id]}" is in conflict: '
                + report.conflicts[gesture_id].description(names)
            )

    @staticmethod
    def matches_can_overlap(first, second):
        all_positions = FINGER_POSITIONS
        if first.palm is not None and second.palm is not None:
            if first.palm != second.palm:
                return False
        for finger in first.fingers.keys() | second.fingers.keys():
            first_allowed = first.fingers.get(finger, all_positions)
            second_allowed = second.fingers.get(finger, all_positions)
            if not first_allowed.intersection(second_allowed):
                return False
        return True


def find_definition(definitions, gesture_id):
    """Return the definition with ``gesture_id``, or None."""
    return next((definition for definition in definitions if definition.id == gesture_id), None)


def ensure_default_gesture_profile(folder=DEFAULT_GESTURE_PROFILE_DIR):
    """Create the default profile folder and seed it with a usable mapping."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    profile = folder / "invoker_profile.json"
    if not profile.exists() and DEFAULT_GESTURE_TEMPLATE.exists():
        shutil.copyfile(DEFAULT_GESTURE_TEMPLATE, profile)
    return profile
