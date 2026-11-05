"""Paint camera frames into a Tk label, on Tk's thread, at a bounded rate."""

import time

import cv2
from PIL import Image, ImageTk

DISPLAY_INTERVAL_SECONDS = 1 / 30


class FramePainter:
    """Draw BGR frames into a label at most ``1 / interval`` times a second.

    The frame loop runs far faster than the camera, so most calls are skipped
    rather than repainting the same image. ``width`` scales frames down, keeping
    their aspect ratio; None keeps the camera size.
    """

    def __init__(self, *, width=None, interval_seconds=DISPLAY_INTERVAL_SECONDS, clock=time.monotonic):
        self.width = width
        self.interval_seconds = interval_seconds
        self.clock = clock
        self._label = None
        self._photo = None
        self._painted_at = None

    def due(self):
        return self._painted_at is None or self.clock() - self._painted_at >= self.interval_seconds

    def paint(self, label, frame):
        """Paint ``frame`` into ``label`` if a repaint is due; returns whether it painted."""
        if frame is None or not self.due():
            return False
        self._painted_at = self.clock()
        height, width = frame.shape[:2]
        if self.width is not None and self.width != width:
            size = (max(1, self.width), max(1, round(height * self.width / width)))
            frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if label is not self._label or self._photo is None or (
            (self._photo.width(), self._photo.height()) != image.size
        ):
            self._label = label
            self._photo = ImageTk.PhotoImage(image, master=label)
            label.configure(image=self._photo)
        else:
            self._photo.paste(image)
        return True

    def forget(self):
        """Drop the image, e.g. after its label was destroyed."""
        self._label = self._photo = None
