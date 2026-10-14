"""Project folders that hold the files the application reads and writes."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_DIR = PROJECT_ROOT / "settings"
GESTURE_PROFILE_DIR = PROJECT_ROOT / "gesture_profiles"
