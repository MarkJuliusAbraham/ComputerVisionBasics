"""Gate initial activation on finger articulation, without a fixed dwell timer."""

from dataclasses import dataclass

from .finger_classifier import FINGER_POSITIONS


@dataclass
class HandMotion:
    timestamp: float
    angles: dict[str, float]
    speeds: dict[str, float]
    candidate_id: str | None = None


class FingerSettlingGate:
    def __init__(self):
        self.enabled = False
        self.max_speed = 90.0
        self._hands = {}

    def configure(self, enabled, max_speed):
        if (enabled, max_speed) != (self.enabled, self.max_speed):
            self.enabled, self.max_speed = enabled, max_speed
            self.reset()

    def reset(self):
        self._hands.clear()

    def finish_frame(self, present_hands):
        self._hands = {key: value for key, value in self._hands.items() if key in present_hands}

    @staticmethod
    def relevant_fingers(definition, definitions, state):
        relevant = {name for name, allowed in definition.match.fingers.items()
                    if allowed != FINGER_POSITIONS}
        for other in definitions:
            if other.id == definition.id:
                continue
            if other.match.palm is not None and other.match.palm != state.palm.value:
                continue
            mismatches = {name for name, allowed in other.match.fingers.items()
                          if name not in state.fingers or state.fingers[name].position.value not in allowed}
            # Also watch a finger that could turn this pose into another gesture.
            if len(mismatches) == 1:
                relevant.update(mismatches)
        return relevant

    def allows(self, state, handedness, definition, definitions, timestamp):
        if not self.enabled:
            return True
        angles = {name: finger.deviation for name, finger in state.fingers.items()}
        previous = self._hands.get(handedness)
        if previous is None or timestamp < previous.timestamp or timestamp - previous.timestamp > .25:
            motion = HandMotion(timestamp, angles, {})
            self._hands[handedness] = motion
        elif timestamp == previous.timestamp:
            motion = previous  # Cached inference cannot count as settled motion.
        else:
            elapsed = timestamp - previous.timestamp
            motion = HandMotion(timestamp, angles, {
                name: abs(angle - previous.angles[name]) / elapsed
                for name, angle in angles.items() if name in previous.angles
            })
            self._hands[handedness] = motion
        motion.candidate_id = definition.id if definition is not None else None
        if definition is None:
            return False
        relevant = self.relevant_fingers(definition, definitions, state)
        if not relevant:
            return True  # A palm-only mapping has no finger articulation to gate.
        return all(name in motion.speeds and motion.speeds[name] <= self.max_speed
                   for name in relevant)
