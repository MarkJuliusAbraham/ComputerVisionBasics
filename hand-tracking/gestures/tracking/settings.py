"""Portable tracking options stored alongside a gesture's mapping."""

from dataclasses import dataclass

from ..hand_landmarks import FINGER_NAMES


@dataclass(frozen=True)
class GestureTrackingSettings:
    fingers: tuple[str, ...] = ("index",)

    def __post_init__(self):
        if (
            not isinstance(self.fingers, tuple)
            or any(not isinstance(name, str) or name not in FINGER_NAMES for name in self.fingers)
        ):
            raise ValueError("Tracked fingers must contain only valid finger names.")
        if len(set(self.fingers)) != len(self.fingers):
            raise ValueError("Tracked fingers cannot contain duplicates.")
        # Canonical ordering prevents checkbox order from creating false changes.
        object.__setattr__(self, "fingers", tuple(name for name in FINGER_NAMES if name in self.fingers))

    def to_dict(self):
        return {"fingers": list(self.fingers)}

    @classmethod
    def from_dict(cls, value, location="tracking"):
        if not isinstance(value, dict):
            raise ValueError(f"{location} must be an object")
        fingers = value.get("fingers", ["index"])
        if not isinstance(fingers, list):
            raise ValueError(f"{location}.fingers must be a list")
        try:
            return cls(tuple(fingers))
        except ValueError as error:
            raise ValueError(f"{location}: {error}") from error

    @classmethod
    def from_gesture(cls, value, location, repeat_fingers=()):
        if "tracking" in value:
            return cls.from_dict(value["tracking"], f"{location}.tracking")
        # Upgrade existing profiles without overriding a saved None selection.
        finger = value.get("tracked_finger", repeat_fingers[0] if repeat_fingers else "index")
        try:
            return cls(()) if finger is None else cls((finger,))
        except ValueError as error:
            raise ValueError(f"{location}.tracked_finger: {error}") from error
