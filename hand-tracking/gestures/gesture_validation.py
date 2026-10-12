"""Report identical hand criteria without involving widgets or command data."""

from dataclasses import dataclass

from .finger_classifier import FINGERS, FINGER_POSITIONS


@dataclass(frozen=True)
class GestureConflict:
    other_gesture_ids: tuple[str, ...] = ()
    with_reset: bool = False

    def description(self, names, *, maximum_names=None):
        visible_ids = self.other_gesture_ids[:maximum_names]
        targets = [f'"{names[gesture_id]}"' for gesture_id in visible_ids]
        remaining = len(self.other_gesture_ids) - len(visible_ids)
        if remaining:
            targets.append(f"and {remaining} other gesture{'s' if remaining != 1 else ''}")
        if self.with_reset:
            targets.append("the universal reset gesture")
        return "Identical hand criteria to " + ", ".join(targets) + "."


@dataclass(frozen=True)
class GestureValidationReport:
    conflicts: dict[str, GestureConflict]

    @property
    def invalid_ids(self):
        return frozenset(self.conflicts)

    def conflict_for(self, gesture_id):
        return self.conflicts.get(gesture_id)


class GestureCriteriaValidator:
    @staticmethod
    def _key(match):
        # An omitted finger and an explicit choice of every classification
        # impose the same constraint. Use all stable categories, independent
        # of the currently displayed segment count.
        return match.palm, tuple(
            frozenset(match.fingers.get(finger, FINGER_POSITIONS))
            for finger in FINGERS
        )

    def validate(self, criteria, reset_match):
        groups = {}
        for gesture_id, match in criteria.items():
            groups.setdefault(self._key(match), []).append(gesture_id)
        reset_key = self._key(reset_match)
        conflicts = {}
        for key, gesture_ids in groups.items():
            with_reset = key == reset_key
            if len(gesture_ids) == 1 and not with_reset:
                continue
            for gesture_id in gesture_ids:
                conflicts[gesture_id] = GestureConflict(
                    tuple(other for other in gesture_ids if other != gesture_id), with_reset,
                )
        return GestureValidationReport(conflicts)
