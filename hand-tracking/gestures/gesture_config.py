import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from gestures.finger_classifier import FINGER_POSITIONS
from gestures.palm_detector import PalmPosition


DEFAULT_GESTURE_PROFILE_DIR = Path(__file__).resolve().parents[1] / "gesture_profiles"
DEFAULT_GESTURE_CONFIG = DEFAULT_GESTURE_PROFILE_DIR / "invoker_profile.json"
DEFAULT_GESTURE_TEMPLATE = Path(__file__).with_name("default_gesture_profile.json")
FINGER_NAMES = {"thumb", "index", "middle", "ring", "pinky"}
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
    repeat_fingers: tuple[str, ...] = ()
    tracked_finger: str | None = None

    def to_dict(self):
        result = {
            "id": self.id,
            "name": self.name,
            "match": self.match.to_dict(),
            "commands": self.commands.to_dict(),
            "tracked_finger": self.tracked_finger,
        }
        if self.repeat_fingers:
            result["repeat_fingers"] = list(self.repeat_fingers)
        return result


@dataclass(frozen=True)
class RepeatSettings:
    initial_displacement: float = 0.03
    distance_threshold: float = 0.09
    min_interval_seconds: float = 0.05
    max_repeats: int = 2

    def to_dict(self):
        return {
            "initial_displacement": self.initial_displacement,
            "distance_threshold": self.distance_threshold,
            "min_interval_seconds": self.min_interval_seconds,
            "max_repeats": self.max_repeats,
        }

    @classmethod
    def from_dict(cls, value):
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise ValueError("repeat_settings must be an object")
        defaults = cls()
        settings = cls(
            initial_displacement=value.get(
                "initial_displacement", defaults.initial_displacement
            ),
            distance_threshold=value.get("distance_threshold", defaults.distance_threshold),
            min_interval_seconds=value.get("min_interval_seconds", defaults.min_interval_seconds),
            max_repeats=value.get("max_repeats", defaults.max_repeats),
        )
        numeric = (
            settings.initial_displacement, settings.distance_threshold,
            settings.min_interval_seconds,
        )
        if any(not isinstance(number, (int, float)) or isinstance(number, bool)
               for number in numeric):
            raise ValueError(
                "Initial displacement, repeat distance, and interval must be numbers"
            )
        if (
            settings.initial_displacement < 0
            or settings.distance_threshold <= 0
            or settings.min_interval_seconds < 0
        ):
            raise ValueError(
                "Initial displacement and interval must be non-negative; "
                "repeat distance must be positive"
            )
        if not isinstance(settings.max_repeats, int) or isinstance(settings.max_repeats, bool) or settings.max_repeats < 0:
            raise ValueError("max_repeats must be a non-negative integer")
        return settings


@dataclass(frozen=True)
class GestureConfig:
    definitions: tuple[GestureDefinition, ...]
    reset_match: GestureMatch
    repeat_settings: RepeatSettings = RepeatSettings()

    def to_dict(self):
        return {
            "version": 1,
            "reset_match": self.reset_match.to_dict(),
            "repeat_settings": self.repeat_settings.to_dict(),
            "gestures": [definition.to_dict() for definition in self.definitions],
        }

    def save(self, path=DEFAULT_GESTURE_CONFIG):
        ids = [definition.id for definition in self.definitions]
        if len(set(ids)) != len(ids):
            raise ValueError("Gesture IDs must be unique")
        if any(
            not isinstance(definition.name, str) or not definition.name.strip()
            for definition in self.definitions
        ):
            raise ValueError("Gesture names cannot be empty")
        self._validate_no_overlaps(self.definitions)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        with open(temporary, "w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=2)
            file.write("\n")
        temporary.replace(target)

    @classmethod
    def load(cls, path=DEFAULT_GESTURE_CONFIG):
        if Path(path) == DEFAULT_GESTURE_CONFIG and not DEFAULT_GESTURE_CONFIG.exists():
            ensure_default_gesture_profile()
        try:
            with open(path, encoding="utf-8") as file:
                raw = json.load(file)
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Could not load gesture config {path}: {error}") from error

        if not isinstance(raw, dict) or raw.get("version") != 1:
            raise ValueError("Gesture config must be an object with version 1")
        raw_definitions = raw.get("gestures")
        if not isinstance(raw_definitions, list) or not raw_definitions:
            raise ValueError("Gesture config must define at least one gesture")

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

            tracked_finger = (
                item["tracked_finger"]
                if "tracked_finger" in item
                else (repeat_fingers[0] if repeat_fingers else "index")
            )
            if tracked_finger is not None and (
                not isinstance(tracked_finger, str)
                or tracked_finger not in FINGER_NAMES
            ):
                raise ValueError(
                    f"{location}.tracked_finger must be one of {sorted(FINGER_NAMES)}"
                )

            definitions.append(GestureDefinition(
                id=gesture_id,
                name=name,
                match=GestureMatch.from_dict(item.get("match"), f"{location}.match"),
                commands=CommandSequence.from_dict(
                    item.get("commands"), f"{location}.commands"
                ),
                repeat_fingers=tuple(repeat_fingers),
                tracked_finger=tracked_finger,
            ))

        cls._validate_no_overlaps(definitions)
        reset_match = GestureMatch.from_dict(raw.get("reset_match"), "reset_match")
        return cls(
            tuple(definitions), reset_match,
            RepeatSettings.from_dict(raw.get("repeat_settings")),
        )

    @staticmethod
    def _validate_no_overlaps(definitions):
        for definition in definitions:
            if definition.match.palm is None and not definition.match.fingers:
                raise ValueError(
                    f"Gesture {definition.id!r} must constrain palm or at least one finger"
                )
        for index, first in enumerate(definitions):
            for second in definitions[index + 1:]:
                if GestureConfig.matches_can_overlap(first.match, second.match):
                    raise ValueError(
                        f"Gestures {first.id!r} and {second.id!r} overlap; "
                        "make their match rules mutually exclusive"
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


def ensure_default_gesture_profile(folder=DEFAULT_GESTURE_PROFILE_DIR):
    """Create the default profile folder and seed it with a usable mapping."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    profile = folder / "invoker_profile.json"
    if not profile.exists() and DEFAULT_GESTURE_TEMPLATE.exists():
        shutil.copyfile(DEFAULT_GESTURE_TEMPLATE, profile)
    return profile
