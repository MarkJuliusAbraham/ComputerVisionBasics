import threading

import cv2


class Camera:
    """Capture frames on one owner thread and publish the latest frame."""

    aspect = 1.0

    def __init__(self, camera_index=1, width=1280, height=720):
        self.width = width
        self.height = height
        self.index = None
        self._requested_index = int(camera_index)
        self._frame = None
        self._status = ("opening", int(camera_index), None)
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stopping = threading.Event()
        self._worker = threading.Thread(target=self._capture_loop, daemon=True)
        self._worker.start()

    @property
    def switching(self):
        return self.status()[0] in ("opening", "switching")

    @property
    def requested_index(self):
        with self._lock:
            return self._requested_index

    @property
    def cap(self):
        # Kept for the application loop's existing unavailable-camera check.
        return self.index is not None

    def request_switch(self, camera_index):
        """Queue a camera change; device handles remain private to the worker."""
        camera_index = int(camera_index)
        with self._lock:
            if self._stopping.is_set():
                return
            self._requested_index = camera_index
            self._frame = None
            state = "switching" if self.index is not None else "opening"
            self._status = (state, camera_index, self.index)
        self._wake.set()

    def status(self):
        with self._lock:
            return self._status

    def read(self):
        with self._lock:
            # The application flips frames in place; keep that from mutating
            # the worker's shared latest-frame buffer between reads.
            return self._frame.copy() if self._frame is not None else None

    def _configure(self, capture):
        capture.set(cv2.CAP_PROP_FPS, 60)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def _publish_status(self, state, requested, active, message=None):
        with self._lock:
            self._status = (state, requested, active, message)
            self.index = active

    def _open(self, index):
        capture = cv2.VideoCapture(index)
        if not capture.isOpened():
            capture.release()
            return None
        self._configure(capture)
        actual_w = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_h = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        if actual_w > 0 and actual_h > 0:
            Camera.aspect = actual_w / actual_h
        return capture

    def _try_open(self, index):
        try:
            return self._open(index), None
        except Exception as exc:
            return None, str(exc)

    def _capture_loop(self):
        capture = None
        active_index = None
        requested_index = self._requested_index
        attempted_index = None
        try:
            while not self._stopping.is_set():
                self._wake.clear()
                with self._lock:
                    requested_index = self._requested_index
                if capture is None or requested_index != attempted_index:
                    if capture is not None:
                        capture.release()
                        capture = None
                    requested = requested_index
                    attempted_index = requested
                    capture, error = self._try_open(requested)
                    if capture is None and active_index is not None and active_index != requested:
                        capture, restore_error = self._try_open(active_index)
                        if capture is not None:
                            error = f"Could not open camera {requested}; restored camera {active_index}"
                        elif restore_error:
                            error = f"Could not open camera {requested} or restore camera {active_index}: {restore_error}"
                    if capture is None:
                        message = error or f"Could not open camera {requested}"
                        self._publish_status("failed", requested, None, message)
                        active_index = None
                        self._wake.wait()
                        continue
                    if error is None:
                        active_index = requested
                    ready_message = error

                try:
                    success, frame = capture.read()
                except Exception as exc:
                    success, frame = False, None
                    failure_message = str(exc)
                else:
                    failure_message = f"Camera {requested_index} stopped returning frames"
                if not success:
                    capture.release()
                    capture = None
                    active_index = None
                    self._publish_status("failed", attempted_index, None, failure_message)
                    continue
                with self._lock:
                    # A switch may have been queued during read().
                    has_pending_switch = self._requested_index != attempted_index
                    if not has_pending_switch:
                        self._frame = frame
                        self._status = ("ready", attempted_index, active_index, ready_message)
                        self.index = active_index
                if has_pending_switch:
                    continue
        finally:
            if capture is not None:
                capture.release()

    def release(self):
        self._stopping.set()
        self._wake.set()
        if self._worker.is_alive():
            self._worker.join(timeout=2)
