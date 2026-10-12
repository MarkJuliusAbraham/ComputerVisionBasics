import json
from pathlib import Path

from gestures.gesture_config import (
    DEFAULT_GESTURE_CONFIG,
    DEFAULT_GESTURE_PROFILE_DIR,
    GestureConfig,
    ensure_default_gesture_profile,
)


PROFILE_SELECTION_PATH = (
    Path(__file__).resolve().parents[1]
    / "settings"
    / "gesture_profile_selection.json"
)


class GestureProfileManager:
    """Tracks profile discovery, active selection, and its persisted location."""

    def __init__(self, selection_path=PROFILE_SELECTION_PATH):
        self.selection_path = Path(selection_path)
        ensure_default_gesture_profile()
        self.source_path = str(DEFAULT_GESTURE_PROFILE_DIR)
        self.active_profile = str(DEFAULT_GESTURE_CONFIG)
        self._load_selection()

    @staticmethod
    def _folder_for(path):
        path = Path(path)
        return path.parent if path.suffix.lower() == ".json" else path

    @staticmethod
    def list_profiles(path):
        folder = GestureProfileManager._folder_for(path)
        if not folder.is_dir():
            return ()
        profiles = []
        for item in sorted(folder.glob("*.json"), key=lambda file: file.name.lower()):
            try:
                GestureConfig.load(item)
            except ValueError:
                continue
            profiles.append(item)
        return tuple(profiles)

    def _load_selection(self):
        try:
            with open(self.selection_path, encoding="utf-8") as file:
                saved = json.load(file)
            if not isinstance(saved, dict):
                raise ValueError("Profile selection file must contain an object")
        except (OSError, json.JSONDecodeError, ValueError):
            self._save_selection()
            return

        source_value = saved.get("source_path")
        source = Path(source_value) if isinstance(source_value, str) and source_value else DEFAULT_GESTURE_PROFILE_DIR
        if source.suffix.lower() == ".json":
            if not source.is_file():
                source = DEFAULT_GESTURE_PROFILE_DIR
        else:
            try:
                source.mkdir(parents=True, exist_ok=True)
                ensure_default_gesture_profile(source)
            except OSError:
                source = DEFAULT_GESTURE_PROFILE_DIR
        self.source_path = str(source)

        active_value = saved.get("active_profile")
        active = Path(active_value) if isinstance(active_value, str) and active_value else DEFAULT_GESTURE_CONFIG
        profiles = self.list_profiles(self.source_path)
        if active not in profiles:
            active = self._preferred_profile(profiles)
        self.active_profile = str(active)
        self._save_selection()

    @staticmethod
    def _preferred_profile(profiles):
        if not profiles:
            return DEFAULT_GESTURE_CONFIG
        return next(
            (profile for profile in profiles if profile.stem == "invoker_profile"),
            profiles[0],
        )

    def _save_selection(self):
        self.selection_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.selection_path.with_name(self.selection_path.name + ".tmp")
        with open(temporary, "w", encoding="utf-8") as file:
            json.dump({
                "source_path": self.source_path,
                "active_profile": self.active_profile,
            }, file, indent=2)
            file.write("\n")
        temporary.replace(self.selection_path)

    def set_location(self, path):
        selected = Path(path)
        if selected.suffix.lower() == ".json":
            if not selected.is_file():
                raise ValueError("Select an existing gesture profile JSON file")
            GestureConfig.load(selected)
            self.source_path = str(selected)
            self.active_profile = str(selected)
        else:
            selected.mkdir(parents=True, exist_ok=True)
            ensure_default_gesture_profile(selected)
            profiles = self.list_profiles(selected)
            current = Path(self.active_profile)
            self.source_path = str(selected)
            self.active_profile = str(
                current if current in profiles else self._preferred_profile(profiles)
            )
        self._save_selection()
        return Path(self.active_profile)

    def select_profile(self, path):
        profile = Path(path)
        if not profile.is_file() or profile.suffix.lower() != ".json":
            raise ValueError("Select an existing .json gesture profile")
        GestureConfig.load(profile)
        self.active_profile = str(profile)
        self.source_path = str(profile.parent)
        self._save_selection()

    def add_profile(self, path):
        profile = Path(path)
        profile.parent.mkdir(parents=True, exist_ok=True)
        if profile.exists():
            raise ValueError(f"A profile named {profile.stem!r} already exists")
        self.active_profile = str(profile)
        self._save_selection()
