"""A shared deviation scale with a variable number of draggable boundaries."""

import tkinter as tk
from tkinter import ttk

from gestures.finger_classifier import FINGER_CATEGORIES_BY_COUNT, finger_categories

from .theme import ThemeMetrics, gesture_bar_background, gesture_classification_color


class FingerThresholdControl(ttk.Frame):
    """Display N classification bands separated by N-1 editable split points."""

    MAX_VALUE = 120

    def __init__(self, master, thresholds, segment_count=4, on_change=None):
        super().__init__(master)
        self.on_change = on_change
        self.theme_name = "Light"
        self.appearance = ThemeMetrics(self)
        self._dragging = None
        self._thresholds = []
        self._categories = ()
        self._canvas_bg = self._get_canvas_background()

        self.canvas = tk.Canvas(
            self, background=self._canvas_bg, highlightthickness=0, borderwidth=0,
        )
        self.canvas.pack(fill="x", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", lambda _event: setattr(self, "_dragging", None))
        self.bind("<<ThemeChanged>>", lambda _event: self.set_theme(self.theme_name))
        self.set_ranges(thresholds, segment_count)
        self.set_theme(self.theme_name)

    @property
    def thresholds(self):
        return list(self._thresholds)

    def set_ranges(self, thresholds, segment_count):
        values = [float(value) for value in thresholds]
        if (
            segment_count not in FINGER_CATEGORIES_BY_COUNT
            or len(values) != segment_count - 1
            or any(not 0 <= value <= self.MAX_VALUE for value in values)
            or any(left >= right for left, right in zip(values, values[1:]))
        ):
            raise ValueError("Deviation ranges need increasing split points for 4–6 segments")
        self._thresholds = values
        self._categories = finger_categories(segment_count)
        self._dragging = None
        self.redraw()

    def set_theme(self, theme_name):
        self.theme_name = theme_name
        self.appearance.refresh()
        self._canvas_bg = self._get_canvas_background()
        height = 5 * self.appearance.font.metrics("linespace") + self.appearance.pixels(44)
        self.canvas.configure(background=self._canvas_bg, height=height)
        self.redraw()

    def _get_canvas_background(self):
        style = ttk.Style(self)
        background = style.lookup("TFrame", "background")
        if background:
            return background
        suffix = "dark" if style.theme_use().endswith("dark") else "light"
        colors = f"::ttk::theme::sv_{suffix}::colors"
        try:
            background = self.tk.call("set", f"{colors}(-bg)")
            if background:
                return background
        except tk.TclError:
            pass
        return self.winfo_toplevel().cget("background")

    def _positions(self):
        width = max(self.canvas.winfo_width(), self.appearance.pixels(220))
        padding = self.appearance.pixels(14)
        left, right = padding, width - padding
        return left, right, [
            left + (right - left) * value / self.MAX_VALUE
            for value in self._thresholds
        ]

    def redraw(self):
        self.canvas.delete("all")
        left, right, markers = self._positions()
        pixels = self.appearance.pixels
        font = self.appearance.font
        line_height = font.metrics("linespace")
        center_y = 3 * line_height + pixels(16)
        radius = pixels(6)
        boundaries = [left, *markers, right]
        colors = [
            gesture_classification_color(self.theme_name, category.semantic_class)
            for category in self._categories
        ]
        for start, end, category, color in zip(
            boundaries, boundaries[1:], self._categories, colors,
        ):
            self.canvas.create_rectangle(
                start, center_y - pixels(5), end, center_y + pixels(5),
                fill=color, outline="", tags=("segment", f"segment-{category.value}"),
            )
            text = category.label.replace(" ", "\n")
            required_width = max(font.measure(word) for word in text.splitlines()) + pixels(6)
            if end - start >= required_width:
                self.canvas.create_text(
                    (start + end) / 2, center_y + pixels(20),
                    text=text, fill=color, anchor="n", font=font,
                    tags=("category-label", f"category-{category.value}"),
                )
        self.canvas.create_rectangle(
            left, center_y - pixels(5), right, center_y + pixels(5),
            outline=gesture_bar_background(self.theme_name),
        )

        foreground = ttk.Style(self).lookup("TLabel", "foreground")
        text_style = {"fill": foreground} if foreground else {}
        value_labels = [f"{value:g}°" for value in self._thresholds]
        label_positions = [
            min(max(marker, font.measure(text) / 2), right + left - font.measure(text) / 2)
            for marker, text in zip(markers, value_labels)
        ]
        label_levels = []
        for index, text in enumerate(value_labels):
            half_width = font.measure(text) / 2
            level = next(
                (
                    candidate for candidate in range(3)
                    if all(
                        candidate != prior_level
                        or abs(label_positions[index] - label_positions[prior_index])
                        >= half_width + font.measure(value_labels[prior_index]) / 2 + pixels(4)
                        for prior_index, prior_level in enumerate(label_levels)
                    )
                ),
                2,
            )
            label_levels.append(level)

        for index, marker in enumerate(markers):
            color = colors[index]
            self.canvas.create_line(
                marker, center_y - pixels(12), marker, center_y + pixels(12),
                fill=color, width=pixels(2),
            )
            self.canvas.create_oval(
                marker - radius, center_y - radius, marker + radius, center_y + radius,
                fill=color, outline=self._canvas_bg,
                tags=("handle", f"handle-{index}"),
            )
            self.canvas.create_text(
                label_positions[index], pixels(2) + label_levels[index] * line_height,
                text=value_labels[index], anchor="n", font=font,
                tags=("threshold-label",), **text_style,
            )

    def _start_drag(self, event):
        _left, _right, markers = self._positions()
        self._dragging = min(range(len(markers)), key=lambda index: abs(markers[index] - event.x))
        self._drag(event)

    def _drag(self, event):
        if self._dragging is None:
            return
        left, right, _markers = self._positions()
        position = min(max(event.x, left), right)
        value = round((position - left) / (right - left) * self.MAX_VALUE, 1)
        index = self._dragging
        previous = self._thresholds[index - 1] if index else 0
        following = (
            self._thresholds[index + 1] if index < len(self._thresholds) - 1
            else self.MAX_VALUE
        )
        gap = min(1.0, (following - previous) / 3)
        lower = previous + gap if index else 0
        upper = following - gap if index < len(self._thresholds) - 1 else self.MAX_VALUE
        value = min(max(value, lower), upper)
        if value != self._thresholds[index]:
            self._thresholds[index] = value
            self.redraw()
            if self.on_change:
                self.on_change()

