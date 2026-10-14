"""Presentation of a rounded classification scale and its color legend."""

import tkinter as tk
from tkinter import ttk

from .classification_legend import ClassificationLegend
from .rounded_bar import RoundedBarRenderer
from .threshold_markers import ThresholdMarkers


class ThresholdScaleView(ttk.Frame):
    def __init__(self, master, appearance, palette_provider):
        super().__init__(master)
        self.appearance = appearance
        self.palette_provider = palette_provider
        self._model = None
        self._palette = None
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.canvas.pack(fill="x")
        self.legend = ClassificationLegend(self, appearance)
        self.legend.pack(fill="x", pady=(0, appearance.pixels(4)))
        self.bar = RoundedBarRenderer(self.canvas)
        self.markers = ThresholdMarkers(self.canvas, appearance)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

    def display(self, model, theme_name):
        self._model = model
        self.appearance.refresh()
        palette = self.palette_provider.palette(theme_name)
        self._palette = palette
        line_height = self.appearance.font.metrics("linespace")
        height = 4 * line_height + self.appearance.pixels(55)
        self.canvas.configure(background=palette.surface, height=height)
        self.legend.display(model.categories, palette)
        self.redraw()

    def bounds(self):
        width = self.canvas.winfo_width()
        if width <= 1:
            width = self.canvas.winfo_reqwidth()
        pixels = self.appearance.pixels
        padding = min(pixels(14), width / 4)
        top = 3 * self.appearance.font.metrics("linespace") + pixels(14)
        return padding, top, width - padding, top + pixels(8)

    def positions(self, model):
        left, _top, right, _bottom = self.bounds()
        return left, right, [
            left + (right - left) * value / model.maximum
            for value in model.thresholds
        ]

    def redraw(self):
        if self._model is None:
            return
        palette = self._palette
        model = self._model
        boundaries = (0, *model.thresholds, model.maximum)
        bands = [
            (start / model.maximum, end / model.maximum, palette.classification(category))
            for start, end, category in zip(boundaries, boundaries[1:], model.categories)
        ]
        bounds = self.bounds()
        self.bar.segments(bounds, bands, palette.track)
        self.markers.draw(
            bounds, model.thresholds, model.maximum, palette,
            left_colors=[color for _start, _end, color in bands[:-1]],
        )
