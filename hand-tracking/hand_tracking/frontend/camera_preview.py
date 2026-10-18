"""Keep the Windows OpenCV event loop separate from Tk's event thread."""

import threading
import logging

import cv2


class CameraPreview:
    """Own a HighGUI window and display only the latest submitted frame.

    Creating, painting, pumping, and destroying the native window all happen
    on its owner thread. In particular, waitKey must never run on Tk's thread:
    the Windows backend dispatches that thread's native messages while the
    OpenCV Python binding has released the GIL.
    """

    def __init__(self, title="Hand Tracking", *, backend=cv2, window_style=None):
        self.title = title
        self.backend = backend
        self.window_style = window_style
        self._pending_frame = None
        self._failure = None
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stopping = threading.Event()
        self._worker = threading.Thread(
            target=self._display_loop, name="camera-preview", daemon=True,
        )
        self._worker.start()

    def show(self, frame):
        """Transfer a completed frame; the caller must not modify it afterward.

        None keeps the previous image visible while the camera is opening.
        Replacing the pending frame prevents a queue of delayed video frames.
        """
        with self._lock:
            if self._failure is not None:
                raise RuntimeError("The camera preview failed") from self._failure
            if self._stopping.is_set() or frame is None:
                return
            self._pending_frame = frame
            self._wake.set()

    def _display_loop(self):
        created = False
        try:
            while not self._stopping.is_set():
                # Continue pumping events even when a camera stops producing
                # frames, so its existing preview remains movable/closable.
                self._wake.wait(timeout=0.01 if created else None)
                with self._lock:
                    self._wake.clear()
                    frame = self._pending_frame
                    self._pending_frame = None
                if self._stopping.is_set():
                    break
                if frame is not None:
                    if not created:
                        self.backend.namedWindow(self.title, self.backend.WINDOW_AUTOSIZE)
                        created = True
                        if self.window_style is not None:
                            self.window_style.apply(self.title)
                    self.backend.imshow(self.title, frame)
                if created:
                    self.backend.waitKey(1)
                    try:
                        created = self.backend.getWindowProperty(
                            self.title, self.backend.WND_PROP_VISIBLE,
                        ) > 0
                    except self.backend.error:
                        # The user may close the native window in waitKey.
                        # Recreate it with the fixed style on the next frame.
                        created = False
        except Exception as error:
            self._record_failure(error)
        finally:
            if created:
                try:
                    self.backend.destroyWindow(self.title)
                except Exception as error:
                    self._record_failure(error)
            with self._lock:
                self._pending_frame = None
                self._stopping.set()

    def _record_failure(self, error):
        with self._lock:
            if self._failure is None:
                self._failure = error

    def close(self):
        """Request shutdown; native cleanup remains on the preview thread."""
        self._stopping.set()
        self._wake.set()
        self._worker.join(timeout=2)
        if self._worker.is_alive():
            logging.getLogger(__name__).warning("Camera preview did not stop within 2 seconds")
