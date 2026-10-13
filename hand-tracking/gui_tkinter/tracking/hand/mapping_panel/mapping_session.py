"""Profile editing and persistence without Tk widget dependencies."""

from copy import deepcopy
from dataclasses import replace
from itertools import product
from pathlib import Path
from uuid import uuid4

from gestures.finger_classifier import FINGERS, finger_categories
from gestures.gesture_config import (
    CommandSequence,
    CommandStep,
    GestureConfig,
    GestureDefinition,
    GestureMatch,
    RepeatSettings,
)
from gestures.profile_manager import GestureProfileManager
from gestures.gesture_validation import GestureCriteriaValidator

from .gesture_draft import GestureDraft
from gui_tkinter.components.movement_draft import MovementSettingsDraft


class MappingSession:
    """Own saved definitions, pending mapping edits, and profile selection."""

    def __init__(self, config_path=None, profile_manager=None, criteria_validator=None):
        self.criteria_validator = (
            criteria_validator if criteria_validator is not None else GestureCriteriaValidator()
        )
        self.profile_manager = (
            profile_manager if profile_manager is not None else GestureProfileManager()
        )
        if config_path is not None:
            self.profile_manager.set_location(config_path)
        self._load(GestureConfig.load(self.profile_manager.active_profile))

    @property
    def config_path(self):
        return Path(self.profile_manager.active_profile)

    @property
    def profile_folder(self):
        source = Path(self.profile_manager.source_path)
        return source.parent if source.suffix.lower() == ".json" else source

    @property
    def definitions(self):
        return self.config.definitions

    @property
    def is_dirty(self):
        return (
            self.drafts != self._baseline or self.reset_draft != self.config.reset_match
            or self.repeat_defaults != self._repeat_baseline
        )

    @property
    def validation_report(self):
        # A half-written command or delay does not prevent criteria feedback.
        return self.criteria_validator.validate(
            {gesture_id: draft.criteria for gesture_id, draft in self.drafts.items()},
            self.reset_draft,
        )

    def _load(self, config):
        self.config = config
        self.drafts = {
            definition.id: GestureDraft.from_definition(definition)
            for definition in config.definitions
        }
        self._baseline = deepcopy(self.drafts)
        self.reset_draft = config.reset_match
        self.repeat_defaults = MovementSettingsDraft.from_settings(config.repeat_settings)
        self._repeat_baseline = self.repeat_defaults

    def update_draft(self, gesture_id, draft):
        if gesture_id not in self.drafts:
            raise KeyError(f"Unknown gesture: {gesture_id}")
        self.drafts[gesture_id] = draft

    def discard(self):
        self.drafts = deepcopy(self._baseline)
        self.reset_draft = self.config.reset_match
        self.repeat_defaults = self._repeat_baseline

    def apply_repeats_to_all(self, repeat):
        self.drafts = {
            gesture_id: replace(draft, repeat=repeat)
            for gesture_id, draft in self.drafts.items()
        }
        self.repeat_defaults = repeat

    def update_reset(self, match):
        self.reset_draft = match

    def build_config(self):
        definitions = tuple(
            self.drafts[definition.id].to_definition(definition)
            for definition in self.definitions
        )
        updated = replace(
            self.config, definitions=definitions, reset_match=self.reset_draft,
            repeat_settings=self.repeat_defaults.to_settings(),
        )
        # Use the profile parser for criteria, conflicts, and command validation.
        return GestureConfig.from_dict(updated.to_dict())

    def save(self):
        config = self.build_config()
        config.save(self.config_path)
        self._load(config)
        return config

    def activate_profile(self, path):
        config = GestureConfig.load(path)
        self.profile_manager.select_profile(path)
        self._load(config)
        return config

    def create_profile(self, folder, profile_name):
        path = Path(folder) / f"{profile_name}.json"
        if path.exists():
            raise ValueError(f"A profile named {profile_name!r} already exists")
        self.build_config().save(path)
        return path

    def save_managed_gestures(self, staged_definitions):
        """Commit names, additions, and deletions while retaining mapping drafts."""
        if not staged_definitions:
            raise ValueError("A profile must contain at least one gesture")
        ids = [definition.id for definition in staged_definitions]
        if len(ids) != len(set(ids)):
            raise ValueError("Gesture IDs must be unique")

        saved = {definition.id: definition for definition in self.definitions}
        definitions = []
        for staged in staged_definitions:
            name = staged.name.strip()
            if not name:
                raise ValueError("Gesture names cannot be empty")
            definitions.append(replace(saved.get(staged.id, staged), name=name))

        updated = replace(self.config, definitions=tuple(definitions))
        # Name edits and deletions must also work while repairing a profile
        # with several conflicts. They do not commit the pending mapping draft.
        updated = GestureConfig.from_dict(updated.to_dict(), allow_conflicts=True)
        updated.save(self.config_path, allow_conflicts=True)

        new_drafts = {}
        new_baseline = {}
        for definition in updated.definitions:
            default = GestureDraft.from_definition(definition)
            pending_default = default
            if definition.id not in self.drafts and self.repeat_defaults != self._repeat_baseline:
                # Newly created gestures inherit pending shared repeat edits
                # without committing those edits through Manage gestures.
                pending_default = replace(default, repeat=self.repeat_defaults)
            new_drafts[definition.id] = self.drafts.get(definition.id, pending_default)
            new_baseline[definition.id] = self._baseline.get(definition.id, default)
        self.config = updated
        self.drafts = new_drafts
        self._baseline = deepcopy(new_baseline)
        return updated

    @staticmethod
    def create_gesture(
        current_definitions, segment_count=4, reset_match=None, *, repeat_settings=None,
    ):
        """Choose an unused pattern for a newly managed gesture."""
        fingers = tuple(FINGERS)
        positions = tuple(category.value for category in finger_categories(segment_count))
        existing = [definition.match for definition in current_definitions]
        if reset_match is not None:
            existing.append(reset_match)
        for palm in (None, "facing_camera", "not_facing_camera"):
            for pattern in product(positions, repeat=len(fingers)):
                match = GestureMatch(
                    palm=palm,
                    fingers={
                        finger: frozenset((position,))
                        for finger, position in zip(fingers, pattern)
                    },
                )
                if all(
                    not GestureConfig.matches_can_overlap(match, current)
                    for current in existing
                ):
                    break
            else:
                continue
            break
        else:
            raise ValueError("No gesture pattern is available outside the command and reset rules")

        existing_ids = {definition.id for definition in current_definitions}
        gesture_id = f"gesture_{uuid4().hex[:8]}"
        while gesture_id in existing_ids:
            gesture_id = f"gesture_{uuid4().hex[:8]}"
        return GestureDefinition(
            id=gesture_id,
            name="New Gesture",
            match=match,
            commands=CommandSequence((CommandStep(type="key_tap", value="a"),)),
            repeat_settings=repeat_settings if repeat_settings is not None else RepeatSettings(),
        )
