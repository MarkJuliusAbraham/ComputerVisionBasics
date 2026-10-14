"""Record all selected fingertips for the hand that started a gesture."""

from .path import FingertipPath


class GesturePathTracker:
    def __init__(self, max_points=2048):
        self.max_points = max_points
        self.gesture_id = None
        self.handedness = None
        self._paths = {}
        self._completed = ()

    @property
    def active(self):
        return self.gesture_id is not None

    @property
    def drawing_paths(self):
        if self.active:
            return tuple(path.drawing for path in self._paths.values() if path.points)
        return self._completed

    def owns_hand(self, handedness):
        return self.active and self.handedness in (None, handedness)

    def start(self, definition, state, handedness):
        self.clear()
        self.gesture_id = definition.id
        self.handedness = handedness
        self._paths = {
            name: FingertipPath(name, self.max_points)
            for name in definition.tracking.fingers
        }
        self.append(state)

    def append(self, state):
        segments = {}
        for name, path in self._paths.items():
            finger = state.fingers.get(name)
            if finger is not None:
                segment = path.append(finger.tip)
                if segment is not None:
                    segments[name] = segment
        return segments

    def mark_repeat(self, finger, point):
        path = self._paths.get(finger)
        if path is not None:
            path.mark_repeat(point)

    def mark_current_repeat(self, gesture_id):
        if self.gesture_id != gesture_id:
            return
        for path in self._paths.values():
            if path.points:
                path.mark_repeat(path.points[-1])

    def finish(self):
        if not self.active:
            return
        self._completed = self.drawing_paths
        self.gesture_id = None
        self.handedness = None
        self._paths = {}

    def finish_missing_hand(self, present_hands):
        if self.active and self.handedness is not None and self.handedness not in present_hands:
            self.finish()
            return True
        return False

    def clear(self):
        self.gesture_id = None
        self.handedness = None
        self._paths = {}
        self._completed = ()
