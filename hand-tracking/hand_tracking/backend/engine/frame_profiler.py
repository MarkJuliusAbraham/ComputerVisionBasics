from contextlib import contextmanager
import time


class FrameProfiler:
    """Report application frame rate at a rolling interval."""

    def __init__(self, enabled=True, report_interval=2.0):
        self.report_interval = report_interval
        self._enabled = bool(enabled)
        self._window_started = time.perf_counter()
        self._frame_count = 0

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        value = bool(value)
        if value != self._enabled:
            self._enabled = value
            self._window_started = time.perf_counter()
            self._frame_count = 0

    @contextmanager
    def measure(self, _stage):
        # Retain the call sites while omitting per-stage timing overhead/data.
        yield

    def finish_frame(self):
        if not self.enabled:
            return None

        self._frame_count += 1
        now = time.perf_counter()
        interval = now - self._window_started
        if interval < self.report_interval:
            return None

        fps = self._frame_count / interval
        self._window_started = now
        self._frame_count = 0
        return fps
