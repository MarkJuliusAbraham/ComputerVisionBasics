import json
import os
from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from typing import Callable, TypeAlias

from landmarker import DEFAULT_MODEL_PATH
from gestures.optimistic.settings import OptimisticTrackingSettings

from gestures.finger_classifier import (
    FINGER_CATEGORIES_BY_COUNT,
    FingerClassifier,
    finger_categories,
)

from .theme_choices import THEMES, resolve_theme


def default_finger_thresholds(segment_count=4):
    """Keep the original four bands and subdivide the higher-bend ranges."""
    return resize_finger_thresholds([15.0, 45.0, 75.0], segment_count)


def resize_finger_thresholds(thresholds, segment_count):
    """Resize a split list while retaining existing values where practical."""
    if segment_count not in FINGER_CATEGORIES_BY_COUNT:
        raise ValueError("Finger segment count must be between 4 and 6")
    values = sorted(float(value) for value in thresholds)
    if len(values) < 2:
        values = [15.0, 45.0, 75.0]
    target_count = segment_count - 1
    while len(values) < target_count:
        insert_before_closed = len(values) - 1
        lower = values[insert_before_closed - 1]
        upper = values[insert_before_closed]
        values.insert(insert_before_closed, (lower + upper) / 2)
    while len(values) > target_count:
        if target_count == 0:
            return []
        # Added bands are inserted immediately before the Closed band, so
        # remove those split points in reverse order when reducing the count.
        values.pop(-2)
    return values

DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "settings.json"
)

UI_SCALES = ("Auto", "100%", "125%", "150%", "175%", "200%")
@dataclass
class SettingsData:
    """Portable values that configure the application."""

    track_hands: bool = True
    profile: bool = True
    theme: str = "Light"
    ui_scale: str = "Auto"
    finger_segment_count: int = 4
    finger_classification_thresholds: list[float] = field(
        default_factory=lambda: default_finger_thresholds(4)
    )
    finger_deviation_calculation: str = "default"
    hand_landmarker_model_path: str = DEFAULT_MODEL_PATH
    optimistic_tracking: OptimisticTrackingSettings = field(default_factory=OptimisticTrackingSettings)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, values):
        fields = cls.__dataclass_fields__
        data = {key: value for key, value in values.items() if key in fields}
        defaults = cls()
        try:
            data["optimistic_tracking"] = OptimisticTrackingSettings.from_dict(data.get("optimistic_tracking"))
        except ValueError:
            data["optimistic_tracking"] = defaults.optimistic_tracking
        if not isinstance(data.get("hand_landmarker_model_path", defaults.hand_landmarker_model_path), str):
            data["hand_landmarker_model_path"] = defaults.hand_landmarker_model_path
        data["theme"] = resolve_theme(data.get("theme", defaults.theme)).name
        try:
            segment_count = int(data.get("finger_segment_count", 0))
        except (TypeError, ValueError, OverflowError):
            segment_count = 0
        if segment_count not in FINGER_CATEGORIES_BY_COUNT:
            existing_thresholds = data.get("finger_classification_thresholds")
            if isinstance(existing_thresholds, list):
                inferred_count = len(existing_thresholds) + 1
            else:
                inferred_count = 4
            segment_count = inferred_count if inferred_count in FINGER_CATEGORIES_BY_COUNT else 4
        data["finger_segment_count"] = segment_count
        # Migrate settings files written before thresholds became an ordered
        # list. The legacy fields are ignored after this one-time conversion.
        if "finger_classification_thresholds" not in data:
            legacy_keys = (
                "finger_straight_threshold",
                "finger_curled_threshold",
                "finger_closed_threshold",
            )
            if any(key in values for key in legacy_keys):
                data["finger_classification_thresholds"] = [
                    values.get("finger_straight_threshold", 15.0),
                    values.get("finger_curled_threshold", 45.0),
                    values.get("finger_closed_threshold", 75.0),
                ]
            else:
                data["finger_classification_thresholds"] = default_finger_thresholds(
                    segment_count
                )
        try:
            thresholds = [float(value) for value in data["finger_classification_thresholds"]]
        except (TypeError, ValueError):
            thresholds = default_finger_thresholds(segment_count)
        if any(not 0.0 <= value <= 120.0 for value in thresholds) or any(
            left >= right for left, right in zip(thresholds, thresholds[1:])
        ):
            thresholds = default_finger_thresholds(segment_count)
        else:
            thresholds = resize_finger_thresholds(thresholds, segment_count)
        data["finger_classification_thresholds"] = thresholds
        for key in ("track_hands", "profile"):
            if key in data and not isinstance(data[key], bool):
                data[key] = getattr(defaults, key)
        if data.get("finger_deviation_calculation") not in ("default", "prototype"):
            data["finger_deviation_calculation"] = defaults.finger_deviation_calculation
        return cls(**data)

    def has_valid_finger_thresholds(self):
        thresholds = self.finger_classification_thresholds
        return (
            self.finger_segment_count in FINGER_CATEGORIES_BY_COUNT
            and len(thresholds) == self.finger_segment_count - 1
            and all(0.0 <= value <= 120.0 for value in thresholds)
            and all(left < right for left, right in zip(thresholds, thresholds[1:]))
        )

    def classify_finger_deviation(self, deviation):
        return FingerClassifier.classify_deviation(
            deviation,
            self.finger_classification_thresholds,
            finger_categories(self.finger_segment_count),
        )


DEFAULTS = SettingsData()
CHOICES = {"theme": THEMES, "ui_scale": UI_SCALES}

# Values submitted by a scoped settings form, before JSON serialization.
SettingsValue: TypeAlias = bool | int | float | str | list[float] | OptimisticTrackingSettings
SettingsValues: TypeAlias = dict[str, SettingsValue]


@dataclass(frozen=True)
class SettingsScope:
    """The settings fields and validation owned by one module or panel."""

    name: str
    fields: tuple[str, ...]
    validator: Callable[[SettingsData], str] | None = None

    def values(self, data: SettingsData) -> SettingsValues:
        return {key: deepcopy(getattr(data, key)) for key in self.fields}

    def merge(self, data: SettingsData, values: SettingsValues) -> SettingsData:
        if set(values) - set(self.fields):
            raise ValueError(f"Unexpected fields for {self.name} settings")
        return replace(data, **deepcopy(values))

    def validation_error(self, data: SettingsData) -> str:
        return self.validator(data) if self.validator is not None else ""


def _validate_hand_settings(data):
    if not data.has_valid_finger_thresholds():
        return "Thresholds must be strictly increasing between 0° and 120°."
    if not isinstance(data.optimistic_tracking, OptimisticTrackingSettings):
        return "Enter valid Optimistic Tracking values."
    return ""


SHARED_SETTINGS_SCOPE = SettingsScope("Application", ("profile", "theme", "ui_scale"))
HAND_SETTINGS_SCOPE = SettingsScope("Hand tracking", (
    "track_hands", "finger_segment_count", "finger_classification_thresholds",
    "finger_deviation_calculation",
    "hand_landmarker_model_path",
    "optimistic_tracking",
), validator=_validate_hand_settings)


class Settings:
    """Owns the settings file and its current SettingsData."""

    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        self.data = SettingsData()
        self.load()

    @staticmethod
    def is_valid_path(path):
        return path.lower().endswith(".json") and os.path.isfile(path)

    def use_file(self, path):
        if not self.is_valid_path(path):
            raise ValueError("Settings file must be an existing .json file")
        self.path = path
        self.load()

    def load(self):
        self.data = SettingsData()
        if not os.path.exists(self.path):
            self.save()
            print(f"Created settings file: {self.path}")
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                loaded = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Could not read {self.path} ({e}); using defaults")
            return
        if isinstance(loaded, dict):
            self.data = SettingsData.from_dict(loaded)
        for key, allowed in CHOICES.items():
            if getattr(self.data, key) not in allowed:
                setattr(self.data, key, getattr(DEFAULTS, key))
        if not self.data.has_valid_finger_thresholds():
            self.data.finger_classification_thresholds = (
                default_finger_thresholds(self.data.finger_segment_count)
            )

    def get(self, key):
        return getattr(self.data, key, None)

    def set(self, key, value):
        if hasattr(self.data, key):
            setattr(self.data, key, value)

    def toggle(self, key):
        self.set(key, not self.get(key))

    def update(self, data):
        updated = data if isinstance(data, SettingsData) else SettingsData.from_dict(data)
        for key, allowed in CHOICES.items():
            if getattr(updated, key) not in allowed:
                raise ValueError(f"Invalid {key}: choose one of {', '.join(allowed)}")
        if not updated.has_valid_finger_thresholds():
            raise ValueError("Finger thresholds must be increasing")
        if not isinstance(updated.optimistic_tracking, OptimisticTrackingSettings):
            raise ValueError("Optimistic Tracking settings must be valid")
        previous = self.data
        self.data = updated
        try:
            self.save()
        except OSError:
            self.data = previous
            raise

    def update_fields(self, values: SettingsValues) -> SettingsData:
        """Commit a panel's fields while preserving every other module's values."""
        self.update(replace(self.data, **deepcopy(values)))
        return self.data

    def save(self):
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data.to_dict(), f, indent=2)
        os.replace(tmp, self.path)
