"""Capture hand criteria from a held pose: countdown, record, then report."""

import tkinter as tk
from tkinter import ttk

from hand_tracking.backend.gestures.pose_capture import PoseCapture

COUNTDOWN_SECONDS = 3
CAPTURE_MS = 1500
# Extra neighbouring bands a straight or closed finger accepts.
ALLOWANCES = {"Allowance: none": 0, "Allowance: 1 band": 1, "Allowance: 2 bands": 2}
DEFAULT_ALLOWANCE = "Allowance: 1 band"


class PoseCaptureControl:
    """Own the capture button, allowance choice, status text, and one capture.

    The button and allowance selector are created in ``button_parent``. ``segment_count`` is read when
    a capture starts; ``on_captured`` receives the resulting GestureMatch.
    """

    def __init__(self, master, button_parent, feed, segment_count, on_captured):
        self.master = master
        self.feed = feed
        self.segment_count = segment_count
        self.on_captured = on_captured
        self.status = tk.StringVar(master)
        self.button = ttk.Button(button_parent, text="Capture from hand", width=18, command=self.toggle)
        self.allowance = tk.StringVar(master, value=DEFAULT_ALLOWANCE)
        self.allowance_selector = ttk.Combobox(
            button_parent, textvariable=self.allowance, values=tuple(ALLOWANCES),
            state="readonly", width=17,
        )
        self._capture = None
        self._unsubscribe = None
        self._pending = None
        master.bind("<Destroy>", self._on_destroy, add="+")

    @property
    def active(self):
        return self._pending is not None or self._unsubscribe is not None

    def toggle(self):
        if self.active:
            self.cancel("Capture cancelled.")
        else:
            self.button.configure(text="Cancel capture")
            self._count_down(COUNTDOWN_SECONDS)

    def _count_down(self, remaining):
        if remaining:
            self.status.set(f"Hold the pose in front of the camera… {remaining}")
            self._pending = self.master.after(1000, self._count_down, remaining - 1)
            return
        self._capture = PoseCapture(self.segment_count())
        self._unsubscribe = self.feed.subscribe(self._record)
        self.status.set("Capturing… keep holding the pose.")
        self._pending = self.master.after(CAPTURE_MS, self._finish)

    def _record(self, records):
        for report in records:
            if self._capture.add(report):
                break

    def _finish(self):
        capture = self._capture
        self._stop()
        match = capture.result(ALLOWANCES[self.allowance.get()])
        if match is None:
            self.status.set("No hand was detected. Check that hand tracking is enabled and not paused.")
            return
        self.status.set(
            f"Captured from the {capture.handedness.lower()} hand ({capture.samples} frames). "
            "Adjust any finger as needed."
        )
        self.on_captured(match)

    def cancel(self, message=""):
        self._stop()
        self.status.set(message)

    def _stop(self):
        if self._pending is not None:
            self.master.after_cancel(self._pending)
            self._pending = None
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        self._capture = None
        if self.button.winfo_exists():
            self.button.configure(text="Capture from hand")

    def _on_destroy(self, event):
        if event.widget is self.master:
            self._stop()
