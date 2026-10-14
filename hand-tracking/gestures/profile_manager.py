import json
from pathlib import Path

from gestures.gesture_config import (
    DEFAULT_GESTURE_CONFIG,
    DEFAULT_GESTURE_PROFILE_DIR,
    GestureConfig,
    ensure_default_gesture_profile,
)
from json_storage import write_json_atomic


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

    # Profile validity by (path, modification time, size). Listing a folder
    # parses only files that are new or changed since they were last checked.
    _validity_cache: dict[tuple[Path, int, int], bool] = {}

    @staticmethod
    def folder_for(path):
        """A profile file's folder, or the path itself when it names a folder."""
        path = Path(path)
        return path.parent if path.suffix.lower() == ".json" else path

    @staticmethod
    def ensure_new_profile_path(path):
        path = Path(path)
        if path.exists():
            raise ValueError(f"A profile named {path.stem!r} already exists")
        return path

    @classmethod
    def _is_valid_profile(cls, path):
        try:
            stat = path.stat()
        except OSError:
            return False
        key = (path, stat.st_mtime_ns, stat.st_size)
        valid = cls._validity_cache.get(key)
        if valid is None:
            try:
                GestureConfig.load(path)
                valid = True
            except ValueError:
                valid = False
            cls._validity_cache[key] = valid
        return valid

    @classmethod
    def list_profiles(cls, path):
        folder = cls.folder_for(path)
        if not folder.is_dir():
            return ()
        return tuple(
            item for item in sorted(folder.glob("*.json"), key=lambda file: file.name.lower())
            if cls._is_valid_profile(item)
        )

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
        write_json_atomic(self.selection_path, {
            "source_path": self.source_path,
            "active_profile": self.active_profile,
        })

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
        profile = self.ensure_new_profile_path(path)
        profile.parent.mkdir(parents=True, exist_ok=True)
        self.active_profile = str(profile)
        self._save_selection()
