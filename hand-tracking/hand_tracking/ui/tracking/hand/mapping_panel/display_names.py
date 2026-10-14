"""Readable, unique names for gesture selection widgets."""

from pathlib import Path


def profile_display_name(path):
    profile = Path(path)
    return profile.stem.replace("_", " ").replace("-", " ").title() or profile.name


def gesture_display_names(definitions):
    """Return definitions paired with labels that never expose internal IDs."""
    occurrences = {}
    used = set()
    result = []
    for definition in definitions:
        name = definition.name or "Unnamed"
        key = name.casefold()
        number = occurrences.get(key, 0) + 1
        label = name if number == 1 else f"{name} ({number})"
        while label.casefold() in used:
            number += 1
            label = f"{name} ({number})"
        occurrences[key] = number
        used.add(label.casefold())
        result.append((definition, label))
    return result
