"""Readable live summary and finger deviations for one hand."""

from tkinter import ttk

from hand_tracking.ui.components.bars.deviation_table_layout import DeviationTableLayout
from hand_tracking.ui.components.deviation_bar import DeviationBar
from .hand_summary import HandSummary


class HandDataPanel(ttk.LabelFrame):
    """Keep hand summary fields and the five finger rows together."""

    def __init__(
        self, master, handedness, theme_name="Light", max_deviation=75.0, *,
        compact=False, palette_provider=None,
    ):
        super().__init__(
            master, text="" if compact else f"{handedness} hand",
            padding=(6, 4) if compact else (14, 12),
        )
        self.compact = compact
        self._theme_name = theme_name
        self._max_deviation = max_deviation
        self._record = None

        if compact:
            ttk.Label(self, text=f"{handedness} hand").pack(anchor="w", pady=(0, 6))
        self.summary = HandSummary(self, row_padding=1 if compact else 4)
        self.summary.pack(fill="x")
        if not compact:
            ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(12, 14))
        self.deviations = DeviationBar(
            self, theme_name=theme_name, max_deviation=max_deviation,
            palette_provider=palette_provider,
            layout=DeviationTableLayout.for_report(compact=compact),
        )
        self.deviations.pack(fill="x")

    def set_data(self, record):
        self._record = record
        self.summary.set_data(record)
        fingers = record.state.fingers if record else None
        self.deviations.set_data(fingers, self._theme_name, self._max_deviation)

    def set_display(self, theme_name, max_deviation):
        self._theme_name = theme_name
        self._max_deviation = max_deviation
        self.set_data(self._record)
