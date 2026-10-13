"""Load and retire model sessions away from the UI thread."""

from contextlib import contextmanager
import threading

from .model_status import ModelStatus


class ModelLoader:
    """One worker owns loading/closing; leases protect active inference submissions."""

    def __init__(self, session_factory, asset):
        self._session_factory = session_factory
        self._asset = asset
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stopping = False
        self._generation = 0
        self._active = None
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
            self._status = ModelStatus("loading", path, self._status.active_path)
            self._wake.set()

    @contextmanager
    def session(self):
        with self._lock:
            yield self._active if self._status.can_detect else None

    def _load_loop(self):
        try:
            while True:
                self._wake.wait()
                with self._lock:
                    self._wake.clear()
                    if self._stopping:
                        break
                    generation = self._generation
                    path = self._status.requested_path
                candidate = None
                error = ""
                if path:
                    try:
                        candidate = self._session_factory(self._asset.read(path))
                    except Exception as failure:
                        error = str(failure).splitlines()[0] if str(failure) else type(failure).__name__
                retired = None
                with self._lock:
                    stale = self._stopping or generation != self._generation
                    if not stale:
                        if candidate is not None or not path:
                            retired = self._active
                            self._active = candidate
                            self._status = ModelStatus("ready" if candidate else "empty", path, path)
                        else:
                            # Preserve a working model if the replacement fails to load.
                            self._status = ModelStatus("failed", path, self._status.active_path, error)
                self._retire(candidate if stale else retired)
        finally:
            with self._lock:
                active, self._active = self._active, None
                self._status = ModelStatus()
            self._retire(active)

    @staticmethod
    def _retire(session):
        if session is not None:
            try:
                session.close()
            except Exception as error:
                print(f"Could not close hand landmarker: {error}")

    def close(self):
        with self._lock:
            self._stopping = True
            self._wake.set()
        self._worker.join()
