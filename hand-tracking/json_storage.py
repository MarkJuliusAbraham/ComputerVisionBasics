"""Crash-safe JSON persistence shared by settings, profiles, and selections."""

import json
from pathlib import Path


def write_json_atomic(path, data, *, trailing_newline=True):
    """Write ``data`` beside ``path`` first, then replace the file in one step.

    A failure while writing leaves the previous file untouched.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    with open(temporary, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        if trailing_newline:
            file.write("\n")
    temporary.replace(target)
