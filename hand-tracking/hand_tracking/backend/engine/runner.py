"""Run the tracking engine on its own thread, apart from the user interface.

Frame processing, gesture handling, and keyboard commands then never wait for
the UI, and the UI never waits for them: it reads the latest snapshot and
sends requests. This matters most on macOS, where Tk's event loop also draws
the camera and is throttled when the app is in the background.

Ordering rule: requests are applied in the order they were made, all before
the next frame is processed. A request to stop commands therefore affects
every frame processed after it was made.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, replace
import logging
import threading

from hand_tracking.backend.engine.engine import FrameResult, TrackingEngine, TrackingSwitches

logger = logging.getLogger(__name__)

# How long the engine waits for a new camera frame before advancing pending
# commands anyway; key holds are timed in tens of milliseconds.
FRAME_WAIT_SECONDS = 0.005


@dataclass(frozen=True)
class EngineSnapshot:
    """The latest result and the switches it was processed with."""

    sequence: int                       # Increases with every published result
    result: FrameResult | None
    switches: TrackingSwitches


Request = Callable[[TrackingEngine], None]


class EngineRunner:
    """Own the engine thread: apply queued requests, process frames, publish results."""

    def __init__(self, engine: TrackingEngine, *, frame_wait_seconds: float = FRAME_WAIT_SECONDS) -> None:
        self.engine = engine
        self.frame_wait_seconds = frame_wait_seconds
        self._requests: deque[Request] = deque()
        self._lock = threading.Lock()
        self._snapshot = EngineSnapshot(0, None, replace(engine.switches))
        self._preview_requested = False
        self._failure: BaseException | None = None
        self._stopping = threading.Event()
        self._thread = threading.Thread(target=self._run, name="tracking-engine", daemon=True)

    # Called from the UI thread ------------------------------------------------

    def start(self) -> None:
        self._thread.start()

    def submit(self, request: Request) -> None:
        """Queue ``request(engine)`` to run on the engine thread before the next frame."""
        with self._lock:
            self._requests.append(request)

    def set_preview_requested(self, requested: bool) -> None:
        """Detect hands without commands, for live previews and pose capture."""
        self._preview_requested = requested

    def snapshot(self) -> EngineSnapshot:
        with self._lock:
            return self._snapshot

    @property
    def failure(self) -> BaseException | None:
        """The error that stopped the engine thread, if any."""
        return self._failure

    def stop(self, timeout: float = 2.0) -> None:
        """Stop after the current frame; pending requests still run first."""
        self._stopping.set()
        if self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout)
            if self._thread.is_alive():
                logger.warning("Tracking engine did not stop within %.0f seconds", timeout)

    # The engine thread --------------------------------------------------------

    def _run(self) -> None:
        try:
            while not self._stopping.is_set():
                self._apply_requests()
                result = self.engine.process_frame(
                    preview_requested=self._preview_requested, wait_seconds=self.frame_wait_seconds,
                )
                if result is not None:
                    self._publish(result)
                    self.engine.finish_frame()
            self._apply_requests()
        except BaseException as error:  # Reported to the UI, which stops the app
            logger.exception("Tracking engine stopped")
            self._failure = error

    def _apply_requests(self) -> None:
        while True:
            with self._lock:
                if not self._requests:
                    return
                request = self._requests.popleft()
            request(self.engine)

    def _publish(self, result: FrameResult) -> None:
        switches = replace(self.engine.switches)
        with self._lock:
            self._snapshot = EngineSnapshot(self._snapshot.sequence + 1, result, switches)
