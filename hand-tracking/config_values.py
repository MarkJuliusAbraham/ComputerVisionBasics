"""Validation and default-merging shared by every serializable settings record."""

import math
from dataclasses import fields


def is_finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_number(value, label, minimum=0):
    if not is_finite_number(value):
        raise ValueError(f"{label} must be a finite number")
    if value < minimum:
        raise ValueError(f"{label} must be at least {minimum}")


def validate_whole_number(value, message):
    """Require a non-negative int (bools are rejected)."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(message)


def merged_fields(cls, value, label, names=None):
    """Return constructor values: saved entries over the dataclass defaults.

    ``None`` means "use every default". ``names`` limits the merge to the
    plain fields; callers convert nested records themselves.
    """
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    defaults = cls()
    names = names if names is not None else tuple(field.name for field in fields(cls))
    return {name: value.get(name, getattr(defaults, name)) for name in names}
