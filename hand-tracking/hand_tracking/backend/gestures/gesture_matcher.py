from hand_tracking.backend.gestures.gesture_config import GestureMatch


class AmbiguousGestureError(RuntimeError):
    """Raised if more than one configured gesture matches the same hand."""


class GestureMatcher:
    @staticmethod
    def matches(rule: GestureMatch, state):
        if rule.palm is not None and state.palm.value != rule.palm:
            return False
        return all(
            state.fingers[name].position.value in allowed
            for name, allowed in rule.fingers.items()
        )

    def find_match(self, definitions, state):
        matches = [
            definition for definition in definitions
            if self.matches(definition.match, state)
        ]
        if len(matches) > 1:
            ids = ", ".join(definition.id for definition in matches)
            raise AmbiguousGestureError(f"Multiple gesture definitions matched: {ids}")
        return matches[0] if matches else None
