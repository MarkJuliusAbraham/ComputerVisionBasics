"""Inference and results belonging to a single loaded Hand Landmarker model."""

import threading
import time
from types import SimpleNamespace

import cv2
import mediapipe as mp


class HandLandmarkerSession:
    def __init__(self, model_data, *, num_hands=1, max_width=None):
        self._model_data = model_data
        self.max_width = max_width
        self._latest = SimpleNamespace(hand_landmarks=[], handedness=[])
        self._last_ts = 0
        self._latency_lock = threading.Lock()
        self._submission_times = {}
        self._latency_total_ms = 0.0
        self._latency_max_ms = 0.0
        self._latency_samples = 0
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_buffer=self._model_data),
            running_mode=mp.tasks.vision.RunningMode.LIVE_STREAM,
            result_callback=self._on_result,
            num_hands=num_hands,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        # MediaPipe validates the model tensors, metadata, and graph contract.
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
        # Results stay within this session, so a retired model cannot overwrite
        # the newly selected model's hand data.
        self._latest = SimpleNamespace(
            hand_landmarks=result.hand_landmarks, handedness=result.handedness,
            hand_world_landmarks=result.hand_world_landmarks, timestamp_ms=timestamp_ms,
        )

    def detect(self, frame):
        h, w = frame.shape[:2]
        if self.max_width and w > self.max_width:
            frame = cv2.resize(frame, (self.max_width, int(h * self.max_width / w)))
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        ts = max(int(time.monotonic() * 1000), self._last_ts + 1)
        self._last_ts = ts
        with self._latency_lock:
            self._submission_times[ts] = time.perf_counter()
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
        with self._latency_lock:
            samples = self._latency_samples
            average_ms = self._latency_total_ms / samples if samples else None
            maximum_ms = self._latency_max_ms if samples else None
            self._latency_samples = 0
            self._latency_total_ms = 0.0
            self._latency_max_ms = 0.0
        return samples, average_ms, maximum_ms

    def close(self):
        self.landmarker.close()
