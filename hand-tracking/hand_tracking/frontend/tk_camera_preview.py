"""Show the camera preview in a Tk window, for systems without the OpenCV preview.

macOS only lets the main thread create and draw windows. Tk already owns that
thread, so OpenCV's own window, which ``CameraPreview`` runs on a worker
thread, cannot be used there. This preview draws on Tk's thread instead: the
frame loop that calls ``show`` already runs there.
"""

import time
import tkinter as tk

import cv2
from PIL import Image, ImageTk

DISPLAY_INTERVAL_SECONDS = 1 / 30


class TkCameraPreview:
    """Display the latest frame, redrawing at most ``1 / interval`` times a second.

    The frame loop runs far faster than the camera, so most calls are skipped
    rather than repainting the same image. ``attach`` supplies the Tk parent
    once the control window exists; frames before that are ignored.
    """

    def __init__(self, title="Hand Tracking", *, interval_seconds=DISPLAY_INTERVAL_SECONDS, clock=time.monotonic):
        self.title = title
        self.interval_seconds = interval_seconds
        self.clock = clock
        self._parent = None
        self._window = None
        self._label = None
        self._photo = None
        self._shown_at = None
        self._closed = False

    def attach(self, parent):
        self._parent = parent

    def show(self, frame):
        """Display a BGR frame; None keeps the previous image visible."""
        if frame is None or self._closed or self._parent is None:
            return
        now = self.clock()
        if self._shown_at is not None and now - self._shown_at < self.interval_seconds:
            return
        self._shown_at = now
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        self._ensure_window()
        if self._photo is None or (self._photo.width(), self._photo.height()) != image.size:
            self._photo = ImageTk.PhotoImage(image, master=self._window)
            self._label.configure(image=self._photo)
        else:
            self._photo.paste(image)

    def _ensure_window(self):
        if self._window is not None and self._window.winfo_exists():
            return
        # Closing the window only hides the preview; the next frame reopens it,
        # as the OpenCV preview does.
        self._window = tk.Toplevel(self._parent)
        self._window.title(self.title)
        self._window.resizable(False, False)
        self._window.protocol("WM_DELETE_WINDOW", self._forget_window)
        self._label = tk.Label(self._window, borderwidth=0, highlightthickness=0)
        self._label.pack()
        self._photo = None

    def _forget_window(self):
        if self._window is not None:
            self._window.destroy()
        self._window = self._label = self._photo = None

    def close(self):
        self._closed = True
        try:
            self._forget_window()
        except tk.TclError:
            pass  # The Tk root may already be destroyed during shutdown.
