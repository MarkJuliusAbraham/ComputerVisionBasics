"""Boundary labels and round drag handles for an editable deviation scale."""

from .boundary_label_layout import BoundaryLabelLayout


class ThresholdMarkers:
    def __init__(self, canvas, appearance, label_layout=None):
        self.canvas = canvas
        self.appearance = appearance
        self.label_layout = label_layout if label_layout is not None else BoundaryLabelLayout()

    def draw(self, bounds, values, maximum, palette, *, left_colors):
        self.canvas.delete("scale-decoration")
        left, top, right, bottom = bounds
        pixels = self.appearance.pixels
        font = self.appearance.font
        line_height = font.metrics("linespace")
        radius = max(pixels(9), (bottom - top) / 2 + pixels(2))
        center = (top + bottom) / 2
        labels = [f"{value:g}°" for value in values]
        widths = [font.measure(label) for label in labels]
        markers = [left + (right - left) * value / maximum for value in values]
        placements = self.label_layout.place(
            markers, widths, left, right, pixels(8),
        )
        for marker, label, (position, level) in zip(markers, labels, placements):
            label_bottom = top - pixels(12) - level * line_height
            self.canvas.create_line(
                position, label_bottom + pixels(2), marker, center,
                fill=palette.track, width=max(1, pixels(1)),
                tags="scale-decoration",
            )
            self.canvas.create_text(
                position, label_bottom, text=label, anchor="s", font=font,
                fill=palette.foreground, tags="scale-decoration",
            )
        for index, (marker, color) in enumerate(zip(markers, left_colors)):
            self.canvas.create_oval(
                marker - radius, center - radius, marker + radius, center + radius,
                fill=color, outline="",
                tags=("scale-decoration", "handle", f"handle-{index}"),
            )
        for x, value, anchor in ((left, 0, "nw"), (right, maximum, "ne")):
            self.canvas.create_text(
                x, bottom + pixels(7), text=f"{value:g}°", anchor=anchor,
                font=font, fill=palette.foreground, tags="scale-decoration",
            )
