"""Interaction controller for a segmented finger deviation scale."""

from tkinter import ttk

from .bars.threshold_ranges import ThresholdRanges
from .bars.threshold_scale import ThresholdScaleView
from .theme import DeviationTheme, ThemeMetrics


class FingerThresholdControl(ttk.Frame):
    """Connect boundary editing to a reusable model and scale view."""

    MAX_VALUE = 120

    def __init__(
        self, master, thresholds, segment_count=4, on_change=None,
        appearance=None, palette_provider=None,
    ):
        super().__init__(master)
        self.on_change = on_change
        self.theme_name = "Light"
        self.appearance = appearance if appearance is not None else ThemeMetrics(self)
        palette_provider = (
            palette_provider if palette_provider is not None else DeviationTheme(self)
        )
        self.ranges = ThresholdRanges(thresholds, segment_count, self.MAX_VALUE)
        self._dragging = None
        self.view = ThresholdScaleView(self, self.appearance, palette_provider)
        self.view.pack(fill="x", expand=True)
        self.canvas = self.view.canvas
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._end_drag)
        self.canvas.bind("<Motion>", self._hover)
        self.canvas.bind("<Leave>", lambda _event: self.canvas.configure(cursor=""))
        self.bind("<<ThemeChanged>>", lambda _event: self.set_theme(self.theme_name))
        self.set_theme(self.theme_name)

    @property
    def thresholds(self):
        return self.ranges.thresholds

    def set_ranges(self, thresholds, segment_count):
        self.ranges.set_ranges(thresholds, segment_count)
        self._dragging = None
        self.redraw()

    def set_theme(self, theme_name):
        self.theme_name = theme_name
        self.redraw()

    def redraw(self):
        self.view.display(self.ranges, self.theme_name)

    def _start_drag(self, event):
        _left, top, _right, bottom = self.view.bounds()
        margin = self.appearance.pixels(8)
        if not top - margin <= event.y <= bottom + margin:
            return
        _left, _right, markers = self.view.positions(self.ranges)
        self._dragging = min(range(len(markers)), key=lambda index: abs(markers[index] - event.x))
        self._drag(event)
        self.redraw()

    def _drag(self, event):
        if self._dragging is None:
            return
        left, right, _markers = self.view.positions(self.ranges)
        position = min(max(event.x, left), right)
        value = (position - left) / max(right - left, 1) * self.ranges.maximum
        if self.ranges.move(self._dragging, value):
            self.redraw()
            if self.on_change:
                self.on_change()

    def _end_drag(self, _event):
        self._dragging = None
        self.redraw()

    def _hover(self, event):
        _left, _right, markers = self.view.positions(self.ranges)
        _left, top, _right, bottom = self.view.bounds()
        near_handle = (
            top - self.appearance.pixels(4) <= event.y <= bottom + self.appearance.pixels(4)
            and any(abs(marker - event.x) <= self.appearance.pixels(10) for marker in markers)
        )
        self.canvas.configure(cursor="hand2" if near_handle else "")
