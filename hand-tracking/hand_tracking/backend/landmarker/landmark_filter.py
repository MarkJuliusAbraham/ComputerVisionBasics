"""Optional coordinate filtering, once per timestamped inference result."""

from copy import copy

from hand_tracking.backend.common.one_euro import OneEuroFilter


class LandmarkFilter:
    def __init__(self):
        self._configuration = (False, 1.0, 0.5)
        self.reset()

    def configure(self, enabled, min_cutoff_hz, beta):
        configuration = (enabled, min_cutoff_hz, beta)
        if configuration != self._configuration:
            self._configuration = configuration
            self.reset()

    def reset(self):
        self._hands = {}
        self._timestamp = None
        self._result = None

    def apply(self, result):
        enabled, cutoff, beta = self._configuration
        if not enabled:
            return result
        timestamp = getattr(result, "timestamp_ms", None)
        if timestamp is None:
            return result
        if timestamp == self._timestamp:
            return self._result
        # Never interpolate over a prolonged loss of tracking or a clock reset.
        if self._timestamp is not None and not 0 < timestamp - self._timestamp <= 250:
            self.reset()
        filtered = copy(result)
        filtered.hand_landmarks = []
        active = {}
        for hand, handedness in zip(result.hand_landmarks, result.handedness):
            name = handedness[0].category_name
            # Separate channels for each handedness and occurrence in the result.
            key = (name, sum(k[0] == name for k in active))
            coordinates = tuple(v for point in hand for v in (point.x, point.y, point.z))
            previous = self._hands.get(key)
            if previous is None or previous[0] != len(coordinates):
                channels = OneEuroFilter(cutoff, beta)
            else:
                channels = previous[1]
            values = channels(timestamp / 1000, coordinates)
            points = []
            for index, point in enumerate(hand):
                point = copy(point)
                point.x, point.y, point.z = values[index * 3:index * 3 + 3]
                points.append(point)
            filtered.hand_landmarks.append(points)
            active[key] = (len(coordinates), channels)
        self._hands = active
        self._timestamp, self._result = timestamp, filtered
        return filtered
