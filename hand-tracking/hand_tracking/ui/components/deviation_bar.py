from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk

from hand_tracking.gestures.hand_landmarks import FINGER_NAMES, finger_label

from .bars.deviation_table_layout import DeviationTableLayout, deviation_ratio
from .bars.rounded_bar import RoundedBarRenderer
from .theme import DeviationTheme, ThemeMetrics


@dataclass
class _DeviationRow:
    """Widgets and the displayed value for one finger's row."""

    name_label: ttk.Label
    canvas: tk.Canvas
    details: tk.StringVar
    label: ttk.Label
    renderer: RoundedBarRenderer
    ratio: float = 0.0
    color: str | None = None
    classification: str | None = None


class DeviationBar(ttk.Frame):
    """Three-column finger deviation table with proportional color bars."""

    def __init__(
        self, master, fingers=None, theme_name="Light", max_deviation=75.0,
        appearance=None, palette_provider=None, layout=None, **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.theme_name = theme_name
        self.max_deviation = max(float(max_deviation), 0.001)
        self.appearance = appearance if appearance is not None else ThemeMetrics(self)
        self.palette_provider = (
            palette_provider if palette_provider is not None else DeviationTheme(self)
        )
        self.layout = layout if layout is not None else DeviationTableLayout()
        self._rows: dict[str, _DeviationRow] = {}

        ttk.Label(self, text="Finger", anchor="w").grid(
            row=0, column=0, sticky="ew", pady=(0, 10)
        )
        ttk.Label(self, text="Deviation", anchor="center", justify="center").grid(
            row=0, column=1, sticky="ew", pady=(0, 10)
        )
        ttk.Label(self, text=self.layout.class_heading, anchor="e").grid(
            row=0, column=2, sticky="ew", pady=(0, 10)
        )

        for row, name in enumerate(FINGER_NAMES, start=1):
            details = tk.StringVar(self, value=self.layout.detail_text(None))
            canvas = tk.Canvas(
                self, height=16, width=120, highlightthickness=0, borderwidth=0
            )
            detail_label = ttk.Label(
                self, textvariable=details, width=1, anchor="e", justify="right"
            )
            name_label = ttk.Label(self, text=finger_label(name), width=1, anchor="w")
            name_label.grid(
                row=row, column=0, sticky="ew", pady=6
            )
            canvas.grid(row=row, column=1, sticky="ew", pady=6)
            detail_label.grid(row=row, column=2, sticky="ew", pady=6)

            record = _DeviationRow(
                name_label, canvas, details, detail_label, RoundedBarRenderer(canvas),
            )
            self._rows[name] = record
            canvas.bind(
                "<Configure>",
                lambda event, item=record: self._draw_bar(item),
            )

        self.set_theme(theme_name)
        self.set_data(fingers)
        self.bind("<<ThemeChanged>>", lambda _event: self.set_theme(self.theme_name))

    def set_theme(self, theme_name):
        """Apply the theme's trough and classification colors to every row."""
        self.theme_name = theme_name
        self.appearance.refresh()
        palette = self.palette_provider.palette(theme_name)
        self.palette = palette
        self.layout.apply(self, self._rows, self.appearance)
        for record in self._rows.values():
            record.canvas.configure(
                background=palette.surface, height=self.appearance.pixels(16),
            )
            self._show_classification(record, record.classification)
            self._draw_bar(record)

    def _show_classification(self, record, classification):
        """Color the row's bar and text for a classification, or reset it."""
        palette = self.palette
        record.classification = classification
        if classification is None:
            record.color = None
            record.label.configure(foreground=palette.foreground)
        else:
            record.color = palette.classification(classification)
            record.label.configure(foreground=palette.classification_text(classification))

    def set_data(self, fingers, theme_name=None, max_deviation=None):
        """Display a mapping of finger names to FingerState values."""
        if theme_name is not None and theme_name != self.theme_name:
            self.set_theme(theme_name)
        if max_deviation is not None:
            self.max_deviation = max(float(max_deviation), 0.001)

        for name, record in self._rows.items():
            finger = fingers.get(name) if fingers else None
            record.details.set(self.layout.detail_text(finger))
            if finger is None:
                record.ratio = 0.0
                self._show_classification(record, None)
            else:
                record.ratio = deviation_ratio(finger.deviation, self.max_deviation)
                self._show_classification(record, finger.position.value)
            self._draw_bar(record)

    def _draw_bar(self, record):
        canvas = record.canvas
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        thickness = min(self.appearance.pixels(self.layout.bar_thickness), height - 2)
        top = (height - thickness) / 2
        record.renderer.progress(
            (1, top, width - 1, top + thickness),
            record.ratio, record.color, self.palette.track,
        )
