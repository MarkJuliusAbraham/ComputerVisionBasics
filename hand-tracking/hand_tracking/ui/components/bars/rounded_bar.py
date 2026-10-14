"""Rounded tracks with reusable canvas items, including clipped color bands."""

import math


class RoundedBarRenderer:
    """Draw live fills and segmented scales with the same rounded geometry."""

    def __init__(self, canvas):
        self.canvas = canvas
        self._items = {}

    def progress(self, bounds, ratio, color, track):
        self._shape("track", bounds, track)
        ratio = min(max(ratio, 0.0), 1.0)
        left, top, right, bottom = bounds
        if color and ratio > 0:
            self._shape("fill", (left, top, left + (right - left) * ratio, bottom), color)
        else:
            self._hide("fill")

    def segments(self, bounds, bands, track):
        """Draw (start fraction, end fraction, color) bands inside one pill."""
        self._shape("track", bounds, track)
        left, _top, right, _bottom = bounds
        for index, (start, end, color) in enumerate(bands):
            self._shape(
                f"band-{index}", bounds, color,
                left + (right - left) * start, left + (right - left) * end,
            )
        for key in self._items:
            if key.startswith("band-") and int(key[5:]) >= len(bands):
                self._hide(key)

    def _shape(self, key, bounds, color, start=None, end=None):
        points = self._points(bounds, start, end)
        if not points:
            self._hide(key)
            return
        previous = self._items.get(key)
        if previous is None:
            item = self.canvas.create_polygon(points, fill=color, outline="")
        else:
            item, old_points, old_color, visible = previous
            if old_points != points:
                self.canvas.coords(item, *points)
            if old_color != color or not visible:
                self.canvas.itemconfigure(item, fill=color, state="normal")
        self._items[key] = (item, points, color, True)

    def _hide(self, key):
        previous = self._items.get(key)
        if previous and previous[3]:
            item, points, color, _visible = previous
            self.canvas.itemconfigure(item, state="hidden")
            self._items[key] = (item, points, color, False)

    @staticmethod
    def _points(bounds, start=None, end=None):
        left, top, right, bottom = bounds
        start = left if start is None else max(start, left)
        end = right if end is None else min(end, right)
        if end <= start or bottom <= top:
            return ()
        radius = min((bottom - top) / 2, (right - left) / 2)
        samples = {start, end}
        # Sample the two outer curves; internal band edges remain straight.
        steps = max(8, math.ceil(radius))
        for index in range(steps + 1):
            offset = radius * (1 - math.cos(index / steps * math.pi / 2))
            for point in (left + offset, right - offset):
                if start < point < end:
                    samples.add(point)
        upper, lower = [], []
        for x in sorted(samples):
            distance = max(left + radius - x, x - (right - radius), 0)
            inset = radius - math.sqrt(max(radius * radius - distance * distance, 0))
            upper.extend((x, top + inset))
            lower[0:0] = (x, bottom - inset)
        return tuple(upper + lower)
