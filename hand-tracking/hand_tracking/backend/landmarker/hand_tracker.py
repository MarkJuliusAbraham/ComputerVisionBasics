"""Hand tracking facade with asynchronously replaceable model sessions."""

from functools import partial
from types import SimpleNamespace

from .landmark_filter import LandmarkFilter

from hand_tracking.backend.landmarker.model_asset import DEFAULT_MODEL_PATH, HandLandmarkerAsset
from hand_tracking.backend.landmarker.model_loader import ModelLoader
from hand_tracking.backend.landmarker.session import HandLandmarkerSession


class HandTracker:
    def __init__(
        self, model_path=DEFAULT_MODEL_PATH, num_hands=1, max_width=None, *,
        asset=None, session_factory=None,
    ):
        self._filter = LandmarkFilter()
        self._filter_session = None
        self.asset = asset if asset is not None else HandLandmarkerAsset()
        factory = session_factory if session_factory is not None else partial(
            HandLandmarkerSession, num_hands=num_hands, max_width=max_width,
        )
        self._loader = ModelLoader(factory, self.asset)
        self._requested_path = None
        self._empty = SimpleNamespace(hand_landmarks=[], handedness=[])
        self.request_model(model_path)

    @property
    def model_status(self):
        return self._loader.status

    def request_model(self, path, *, force=False):
        try:
            selected = str(self.asset.resolve(path)) if path else ""
        except (OSError, ValueError, RuntimeError):
            selected = str(path)  # The loader reports malformed paths without closing the UI.
        if force or selected != self._requested_path:
            self._requested_path = selected
            self._loader.request(selected)

    def configure_filter(self, settings):
        self._filter.configure(settings.one_euro_enabled, settings.one_euro_min_cutoff_hz, settings.one_euro_beta)

    def detect(self, frame):
        with self._loader.session() as session:
            if session is not self._filter_session:
                self._filter.reset()
                self._filter_session = session
            return self._filter.apply(session.detect(frame)) if session is not None else self._empty

    def take_latency_stats(self):
        with self._loader.session() as session:
            return session.take_latency_stats() if session is not None else (0, None, None)

    def close(self):
        self._loader.close()
