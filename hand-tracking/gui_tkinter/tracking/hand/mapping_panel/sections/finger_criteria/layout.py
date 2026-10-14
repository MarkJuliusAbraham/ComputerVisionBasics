"""One sizing policy shared by the two finger criteria tables."""

from dataclasses import dataclass
from gui_tkinter.core.idle_refresh import IdleRefresh

from ..criteria_options import (
    CATEGORY_LABELS, CUSTOM_CLASSIFICATIONS, FINGER_NAMES, FingerCriteriaOptions,
)


@dataclass(frozen=True)
class FingerTableMetrics:
    label_width: int
    heading_height: int
    row_height: int
    divider_height: int
    preferred_width: int
    height: int


class FingerCriteriaLayout:
    """Reserve equal mode sizes and ignore unrelated ttk style notifications."""

    def __init__(self, owner, appearance, tables):
        self.owner = owner
        self.appearance = appearance
        self.tables = tables
        self.metrics = None
        self.refresh_request = IdleRefresh(owner, self.refresh, event="<<ThemeChanged>>")

    @property
    def label_width(self):
        return self.appearance.font.measure("Palm orientation") + self.appearance.pixels(16)

    def schedule_refresh(self, _event=None):
        self.refresh_request.schedule()

    def refresh(self):
        if not self.owner.winfo_exists():
            return
        self.appearance.refresh()
        metrics = self._measure()
        if metrics == self.metrics:
            return
        for table in self.tables:
            table.apply_metrics(metrics)
        self.owner.configure(width=metrics.preferred_width, height=metrics.height)
        self.metrics = metrics

    def _measure(self):
        appearance = self.appearance
        spacing = appearance.pixels(12)
        label_width = self.label_width
        heading_height = 3 * appearance.font.metrics("linespace") + spacing
        row_height = max(
            control.winfo_reqheight() for table in self.tables for control in table.controls
        ) + spacing
        divider_height = max(2, appearance.pixels(1))
        # Use the whole supported vocabulary as a width hint so switching
        # modes, gestures, or segment counts does not change the requested size.
        simple_labels = {CUSTOM_CLASSIFICATIONS}
        for count in (4, 5, 6):
            simple_labels.update(FingerCriteriaOptions(count).simple_choices)
        simple_width = max(appearance.font.measure(label) for label in simple_labels)
        simple_width += appearance.pixels(44)
        heading_words = ["(inactive)"] + [
            word for label in CATEGORY_LABELS.values() for word in label.title().split()
        ]
        column_hint = max(appearance.heading_font.measure(word) for word in heading_words)
        column_hint += appearance.pixels(16)
        return FingerTableMetrics(
            label_width=label_width,
            heading_height=heading_height,
            row_height=row_height,
            divider_height=divider_height,
            preferred_width=label_width + max(simple_width, len(CATEGORY_LABELS) * column_hint),
            height=heading_height + len(FINGER_NAMES) * (row_height + divider_height),
        )
