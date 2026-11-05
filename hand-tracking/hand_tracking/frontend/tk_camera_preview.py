"""Show the camera preview in a Tk window, for systems without the OpenCV preview.

macOS only lets the main thread create and draw windows. Tk already owns that
thread, so OpenCV's own window, which ``CameraPreview`` runs on a worker
thread, cannot be used there. This preview draws on Tk's thread instead: the
frame loop that calls ``show`` already runs there.
"""

import tkinter as tk

from hand_tracking.frontend.components.frame_painter import FramePainter


class TkCameraPreview:
    """Display the latest frame in its own window.

    ``attach`` supplies the Tk parent once the control window exists; frames
    before that are ignored. A hidden preview ignores frames and closes its
    window, as while the overlay shows the camera instead.
    """

    def __init__(self, title="Hand Tracking", *, painter=None):
        self.title = title
        self.painter = painter if painter is not None else FramePainter()
        self._parent = None
        self._window = None
        self._label = None
        self._visible = True
        self._closed = False

    def attach(self, parent):
        self._parent = parent

    def set_visible(self, visible):
        self._visible = visible
        if not visible:
            self._forget_window()

    def show(self, frame):
        """Display a BGR frame; None keeps the previous image visible."""
        if frame is None or self._closed or not self._visible or self._parent is None:
            return
        if not self.painter.due():
            return
        self._ensure_window()
        self.painter.paint(self._label, frame)

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

    def _forget_window(self):
        if self._window is not None:
            try:
                self._window.destroy()
            except tk.TclError:
                pass  # The Tk root may already be destroyed during shutdown.
        self._window = self._label = None
        self.painter.forget()

    def close(self):
        self._closed = True
        self._forget_window()
