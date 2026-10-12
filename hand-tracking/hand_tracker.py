import time
from pathlib import Path
import threading
from types import SimpleNamespace

import cv2
import mediapipe as mp


MODEL_PATH = Path(__file__).resolve().parent / "tasks" / "hand_landmarker.task"

# Stand-in until the first real result arrives
_EMPTY = SimpleNamespace(hand_landmarks=[], handedness=[])


class HandTracker:
    """Handles MediaPipe hand landmark detection (async, LIVE_STREAM mode)."""

    def __init__(self, model_path=MODEL_PATH, num_hands=1, max_width=None):
        self.max_width = max_width
        self._latest = _EMPTY
        self._last_ts = 0
        self._latency_lock = threading.Lock()
        self._submission_times = {}
        self._latency_total_ms = 0.0
        self._latency_max_ms = 0.0
        self._latency_samples = 0
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.LIVE_STREAM,
            result_callback=self._on_result,
            num_hands=num_hands,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self.landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)

    def _on_result(self, result, output_image, timestamp_ms):
        completed_at = time.perf_counter()
        with self._latency_lock:
            submitted_at = self._submission_times.pop(timestamp_ms, None)
            if submitted_at is not None:
                latency_ms = (completed_at - submitted_at) * 1000
                self._latency_total_ms += latency_ms
                self._latency_max_ms = max(self._latency_max_ms, latency_ms)
                self._latency_samples += 1
        # Runs on MediaPipe's thread; a plain reference swap is safe here.
        self._latest = result

    def detect(self, frame):
        """Submit a frame for inference and return the most recent result."""
        h, w = frame.shape[:2]
        if self.max_width and w > self.max_width:
            scale = self.max_width / w
            frame = cv2.resize(frame, (self.max_width, int(h * scale)))

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Real clock time, forced strictly increasing as MediaPipe requires
        ts = max(int(time.monotonic() * 1000), self._last_ts + 1)
        self._last_ts = ts

        submitted_at = time.perf_counter()
        with self._latency_lock:
            self._submission_times[ts] = submitted_at
            # LIVE_STREAM can drop frames; keep unmatched timestamps bounded.
            if len(self._submission_times) > 256:
                self._submission_times.pop(next(iter(self._submission_times)))
        try:
            self.landmarker.detect_async(mp_image, ts)
        except Exception:
            with self._latency_lock:
                self._submission_times.pop(ts, None)
            raise
        return self._latest

    def take_latency_stats(self):
        """Return (samples, average_ms, maximum_ms) since the previous read."""
        with self._latency_lock:
            samples = self._latency_samples
            average_ms = (
                self._latency_total_ms / samples if samples else None
            )
            maximum_ms = self._latency_max_ms if samples else None
            self._latency_samples = 0
            self._latency_total_ms = 0.0
            self._latency_max_ms = 0.0
        return samples, average_ms, maximum_ms

    def close(self):
        self.landmarker.close()
