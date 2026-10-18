"""Load and retire model sessions away from the UI thread."""

from contextlib import contextmanager
from dataclasses import dataclass
import logging
import threading

from .model_status import ModelPhase, ModelStatus


logger = logging.getLogger(__name__)


@dataclass(eq=False)
class _SessionSlot:
    session: object
    users: int = 0
    retired: bool = False


class ModelLoader:
    """One worker owns loading/closing; leases protect active inference submissions."""

    def __init__(self, session_factory, asset):
        self._session_factory = session_factory
        self._asset = asset
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stopping = False
        self._generation = 0
        self._request_pending = False
        self._active = None
        self._retired = []
        self._status = ModelStatus()
        self._worker = threading.Thread(target=self._load_loop, name="hand-model-loader", daemon=True)
        self._worker.start()

    @property
    def status(self):
        with self._lock:
            return self._status

    def request(self, path):
        with self._lock:
            if self._stopping:
                return
            self._generation += 1
            self._request_pending = True
            self._status = ModelStatus(ModelPhase.LOADING, path, self._status.active_path)
            self._wake.set()

    @contextmanager
    def session(self):
        """Lease a session without holding the management lock over native work."""
        with self._lock:
            slot = self._active if not self._stopping and self._status.can_detect else None
            if slot is not None:
                slot.users += 1
        try:
            yield slot.session if slot is not None else None
        finally:
            if slot is not None:
                with self._lock:
                    slot.users -= 1
                    if slot.retired and slot.users == 0:
                        self._wake.set()

    def _load_loop(self):
        while True:
            self._wake.wait()
            with self._lock:
                self._wake.clear()
                idle = [slot for slot in self._retired if slot.users == 0]
                self._retired = [slot for slot in self._retired if slot.users != 0]
                finished = self._stopping and not self._retired
                request = None
                if not self._stopping and self._request_pending:
                    request = self._generation, self._status.requested_path
                    self._request_pending = False
            for slot in idle:
                self._retire(slot.session)
            if finished:
                return
            if request is not None:
                self._load(*request)

    def _load(self, generation, path):
        candidate = None
        error = ""
        if path:
            try:
                candidate = self._session_factory(self._asset.read(path))
            except Exception as failure:
                logger.exception("Could not load hand landmarker from %s", path)
                error = str(failure).splitlines()[0] if str(failure) else type(failure).__name__
        with self._lock:
            stale = self._stopping or generation != self._generation
            if stale:
                self._queue_retirement(_SessionSlot(candidate) if candidate is not None else None)
            elif candidate is not None or not path:
                self._queue_retirement(self._active)
                self._active = _SessionSlot(candidate) if candidate is not None else None
                self._status = ModelStatus(
                    ModelPhase.READY if candidate is not None else ModelPhase.EMPTY, path, path,
                )
            else:
                # Preserve a working model if the replacement fails to load.
                self._status = ModelStatus(ModelPhase.FAILED, path, self._status.active_path, error)
            self._wake.set()

    def _queue_retirement(self, slot):
        """Called under the lock; only the worker closes retired sessions."""
        if slot is not None:
            slot.retired = True
            self._retired.append(slot)

    @staticmethod
    def _retire(session):
        if session is not None:
            try:
                session.close()
            except Exception:
                logger.exception("Could not close hand landmarker")

    def close(self, timeout=1.0):
        """Stop accepting leases and wait at most timeout seconds for native cleanup.

        False means the daemon worker is still loading, closing, or waiting for a
        lease to finish. It continues cleanup when that work returns.
        """
        with self._lock:
            self._stopping = True
            self._queue_retirement(self._active)
            self._active = None
            self._status = ModelStatus()
            self._wake.set()
        self._worker.join(timeout=max(0.0, timeout))
        stopped = not self._worker.is_alive()
        if not stopped:
            logger.warning("Hand model worker did not stop within %.2f seconds; native cleanup is pending", timeout)
        return stopped
