import json
import os
from dataclasses import asdict, dataclass

DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "settings.json"
)

THEMES = ("Light", "Dark")
UI_SCALES = ("Auto", "100%", "125%", "150%", "175%", "200%")


@dataclass
class SettingsData:
    """Portable values that configure the application."""

    track_hands: bool = True
    profile: bool = True
    theme: str = "Light"
    ui_scale: str = "Auto"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, values):
        fields = cls.__dataclass_fields__
        return cls(**{key: value for key, value in values.items() if key in fields})


DEFAULTS = SettingsData()
CHOICES = {"theme": THEMES, "ui_scale": UI_SCALES}


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
            self.data = SettingsData.from_dict({**self.data.to_dict(), **loaded})
        for key, allowed in CHOICES.items():
            if getattr(self.data, key) not in allowed:
                setattr(self.data, key, getattr(DEFAULTS, key))

    def get(self, key):
        return getattr(self.data, key, None)

    def set(self, key, value):
        if hasattr(self.data, key):
            setattr(self.data, key, value)

    def toggle(self, key):
        self.set(key, not self.get(key))

    def update(self, data):
        self.data = data if isinstance(data, SettingsData) else SettingsData.from_dict(data)
        self.save()

    def save(self):
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data.to_dict(), f, indent=2)
        os.replace(tmp, self.path)
