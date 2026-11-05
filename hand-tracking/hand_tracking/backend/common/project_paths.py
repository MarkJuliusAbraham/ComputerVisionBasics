"""Project folders that hold the files the application reads and writes.

Saved paths inside the project are stored relative to it with ``/``
separators, so settings keep working when the project folder moves or is
opened on another operating system. A saved absolute path from a different
operating system (``C:\\...`` read on macOS, ``/Users/...`` read on Windows)
names nothing here, so readers fall back to their defaults.
"""

import os
from pathlib import Path, PureWindowsPath

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SETTINGS_DIR = PROJECT_ROOT / "settings"
GESTURE_PROFILE_DIR = PROJECT_ROOT / "gesture_profiles"


def is_foreign_path(text: str, *, windows: bool | None = None) -> bool:
    """Whether saved path text is an absolute path from another operating system."""
    windows = os.name == "nt" if windows is None else windows
    if windows:
        return text.startswith("/") and not text.startswith("//")
    return bool(PureWindowsPath(text).drive) or "\\" in text


def resolve_saved_path(text: str, default: Path, *, windows: bool | None = None) -> Path:
    """An absolute path for saved text: relative to the project, or ``default`` if foreign."""
    if not text or is_foreign_path(text, windows=windows):
        return Path(default)
    path = Path(text)  # Saved relative paths use "/", which both systems accept.
    return path if path.is_absolute() else PROJECT_ROOT / path


def portable_path(path) -> str:
    """Text to save: project-relative with ``/`` inside the project, else absolute."""
    path = Path(path)
    absolute = path if path.is_absolute() else PROJECT_ROOT / path
    try:
        return absolute.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(absolute)
