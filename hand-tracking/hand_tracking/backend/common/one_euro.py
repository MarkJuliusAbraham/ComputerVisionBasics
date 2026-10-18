"""One Euro filter for jittery landmark positions.

Casiez, Roussel and Vogel, "1€ Filter: A Simple Speed-based Low-pass Filter
for Noisy Input in Interactive Systems" (CHI 2012). A low-pass filter whose
cutoff rises with the filtered speed: slow or resting motion is smoothed
heavily, removing jitter, while fast motion is followed with little lag.
MediaPipe's own LandmarksSmoothingCalculator uses the same filter, but the
Tasks hand landmarker does not apply it, so its landmarks arrive unsmoothed.
"""

import math


def smoothing_factor(cutoff_hz, elapsed_seconds):
    tau = 1 / (2 * math.pi * cutoff_hz)
    return 1 / (1 + tau / elapsed_seconds)


class OneEuroFilter:
    """Filter a fixed-length tuple of values, one independent channel each.

    ``min_cutoff_hz`` sets the smoothing at rest (lower removes more jitter);
    ``beta`` sets how quickly the cutoff rises with speed (higher reduces lag).
    """

    def __init__(self, min_cutoff_hz, beta, derivative_cutoff_hz=1.0):
        if min_cutoff_hz <= 0 or derivative_cutoff_hz <= 0:
            raise ValueError("One Euro cutoff frequencies must be greater than zero")
        self.min_cutoff_hz = min_cutoff_hz
        self.beta = beta
        self.derivative_cutoff_hz = derivative_cutoff_hz
        self._time = None
        self._value = None
        self._speed = None

    def reset(self):
        self._time = self._value = self._speed = None

    def __call__(self, time, value):
        value = tuple(value)
        if self._value is None:
            self._time, self._value, self._speed = time, value, (0.0,) * len(value)
            return value
        elapsed = time - self._time
        if elapsed <= 0:
            return self._value
        derivative_factor = smoothing_factor(self.derivative_cutoff_hz, elapsed)
        speed = tuple(
            previous + derivative_factor * ((current - last) / elapsed - previous)
            for current, last, previous in zip(value, self._value, self._speed)
        )
        filtered = tuple(
            last + smoothing_factor(self.min_cutoff_hz + self.beta * abs(rate), elapsed) * (current - last)
            for current, last, rate in zip(value, self._value, speed)
        )
        self._time, self._value, self._speed = time, filtered, speed
        return filtered
