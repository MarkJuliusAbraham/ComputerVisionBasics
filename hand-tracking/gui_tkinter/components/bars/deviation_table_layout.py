"""Reusable presentation and sizing for a three-column deviation table."""

from dataclasses import dataclass

from gestures.finger_classifier import finger_categories


@dataclass(frozen=True)
class DeviationTableLayout:
    """Keep the bar centered between equal, content-sized outside columns."""

    show_score: bool = True
    bar_thickness: int = 8
    minimum_bar_width: int = 120

    @property
    def class_heading(self):
        return "Score / class" if self.show_score else "Class"

    def detail_text(self, finger):
        if finger is None:
            return "—\n—" if self.show_score else "—"
        label = getattr(
            finger.position, "label", finger.position.value.replace("_", " ").title(),
        )
        if self.show_score:
            return f"{finger.deviation:.1f}°\n{label}"
        return label.replace(" ", "\n")

    def apply(self, table, rows, appearance):
        font = appearance.font
        pixels = appearance.pixels
        labels = ["Finger", self.class_heading, *(name.title() for name in rows)]
        for category in finger_categories(6):
            labels.extend(
                (category.label,) if self.show_score else category.label.split(),
            )
        if self.show_score:
            labels.append("120.0°")
        gap = pixels(8)
        flank_width = max(font.measure(label) for label in labels) + gap
        for column in (0, 2):
            table.columnconfigure(
                column, weight=0, minsize=flank_width, uniform="deviation-labels",
            )
        table.columnconfigure(1, weight=1, minsize=pixels(self.minimum_bar_width))
        row_padding = pixels(6)
        # Two-line classifications get the same row space as single-line ones.
        row_height = 2 * font.metrics("linespace") + 2 * row_padding
        for row, record in enumerate(rows.values(), start=1):
            table.rowconfigure(row, minsize=row_height)
            record["name_label"].grid_configure(padx=(0, gap), pady=row_padding)
            record["label"].grid_configure(padx=(gap, 0), pady=row_padding)
            record["canvas"].grid_configure(pady=row_padding)
