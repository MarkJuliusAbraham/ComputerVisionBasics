from collections import defaultdict
from contextlib import contextmanager
import time


class FrameProfiler:
    """Collect low-overhead frame-stage timings and report rolling summaries."""

    def __init__(self, enabled=True, report_interval=2.0):
        self.enabled = enabled
        self.report_interval = report_interval
        self._window_started = time.perf_counter()
        self._frame_started = None
        self._frame_count = 0
        self._stage_totals = defaultdict(float)
        self._stage_max = defaultdict(float)
        self._stage_counts = defaultdict(int)
        self._frame_total = 0.0
        self._frame_max = 0.0

    def begin_frame(self):
        if self.enabled:
            self._frame_started = time.perf_counter()

    @contextmanager
    def measure(self, stage):
        if not self.enabled:
            yield
            return
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - started
            self._stage_totals[stage] += elapsed
            self._stage_counts[stage] += 1
            self._stage_max[stage] = max(self._stage_max[stage], elapsed)

    def finish_frame(self):
        if not self.enabled or self._frame_started is None:
            return None
        elapsed = time.perf_counter() - self._frame_started
        self._frame_total += elapsed
        self._frame_max = max(self._frame_max, elapsed)
        self._frame_count += 1
        self._frame_started = None

        now = time.perf_counter()
        interval = now - self._window_started
        if interval < self.report_interval:
            return None

        average_frame_ms = self._frame_total * 1000 / self._frame_count
        frame_fps = self._frame_count / interval
        stages = []
        for name in sorted(self._stage_totals):
            count = self._stage_counts[name]
            average_ms = self._stage_totals[name] * 1000 / count
            maximum_ms = self._stage_max[name] * 1000
            stages.append(f"{name}={average_ms:.2f}/{maximum_ms:.2f}ms")

        summary = (
            f"Frame profile: {frame_fps:.1f} fps, "
            f"callback avg/max {average_frame_ms:.2f}/{self._frame_max * 1000:.2f}ms"
        )
        if stages:
            summary += " | " + ", ".join(stages)

        self._window_started = now
        self._frame_count = 0
        self._stage_totals.clear()
        self._stage_max.clear()
        self._stage_counts.clear()
        self._frame_total = 0.0
        self._frame_max = 0.0
        return summary
