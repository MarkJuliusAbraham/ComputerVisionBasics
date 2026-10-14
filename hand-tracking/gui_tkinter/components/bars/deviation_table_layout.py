"""Reusable presentation and sizing for a three-column deviation table."""

from dataclasses import dataclass

from gestures.finger_classifier import ALL_FINGER_CATEGORIES
from gestures.finger_thresholds import MAX_DEVIATION_DEGREES
from gestures.hand_landmarks import FINGER_NAMES, finger_label


def deviation_ratio(deviation, max_deviation):
    """Bar fill fraction for a deviation, clamped to 0..1."""
    return min(max(deviation / max(max_deviation, 0.001), 0.0), 1.0)


@dataclass(frozen=True)
class DeviationTableLayout:
    """Keep the bar centered between equal, content-sized outside columns."""

    show_score: bool = True
    bar_thickness: int = 8
    minimum_bar_width: int = 120

    @classmethod
    def for_report(cls, *, compact):
        """The class-only table used by hand reports and the desktop overlay."""
        return cls(
            show_score=False, bar_thickness=3 if compact else 5,
            minimum_bar_width=120 if compact else 160,
        )

    @property
    def class_heading(self):
        return "Score / class" if self.show_score else "Class"

    def detail_text(self, finger):
        if finger is None:
            return "—\n—" if self.show_score else "—"
        label = finger.position.label
        if self.show_score:
            return f"{finger.deviation:.1f}°\n{label}"
        return label.replace(" ", "\n")

    def flank_labels(self):
        """Every text that can appear in the outside columns, for sizing them."""
        labels = ["Finger", self.class_heading, *(finger_label(name) for name in FINGER_NAMES)]
        for category in ALL_FINGER_CATEGORIES:
            labels.extend(
                (category.label,) if self.show_score else category.label.split(),
            )
        if self.show_score:
            labels.append(f"{MAX_DEVIATION_DEGREES:.1f}°")
        return labels

    def apply(self, table, rows, appearance):
        font = appearance.font
        pixels = appearance.pixels
        gap = pixels(8)
        flank_width = max(font.measure(label) for label in self.flank_labels()) + gap
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
            record.name_label.grid_configure(padx=(0, gap), pady=row_padding)
            record.label.grid_configure(padx=(gap, 0), pady=row_padding)
            record.canvas.grid_configure(pady=row_padding)
