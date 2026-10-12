import tkinter as tk
from tkinter import ttk

from .bars.deviation_table_layout import DeviationTableLayout
from .bars.rounded_bar import RoundedBarRenderer
from .theme import DeviationTheme, ThemeMetrics


class DeviationBar(ttk.Frame):
    """Three-column finger deviation table with proportional color bars."""

    FINGERS = ("thumb", "index", "middle", "ring", "pinky")
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
        self._rows = {}

        ttk.Label(self, text="Finger", anchor="w").grid(
            row=0, column=0, sticky="ew", pady=(0, 10)
        )
        ttk.Label(self, text="Deviation", anchor="center", justify="center").grid(
            row=0, column=1, sticky="ew", pady=(0, 10)
        )
        ttk.Label(self, text=self.layout.class_heading, anchor="e").grid(
            row=0, column=2, sticky="ew", pady=(0, 10)
        )

        for row, name in enumerate(self.FINGERS, start=1):
            details = tk.StringVar(self, value=self.layout.detail_text(None))
            canvas = tk.Canvas(
                self, height=16, width=120, highlightthickness=0, borderwidth=0
            )
            detail_label = ttk.Label(
                self, textvariable=details, width=1, anchor="e", justify="right"
            )
            name_label = ttk.Label(self, text=name.title(), width=1, anchor="w")
            name_label.grid(
                row=row, column=0, sticky="ew", pady=6
            )
            canvas.grid(row=row, column=1, sticky="ew", pady=6)
            detail_label.grid(row=row, column=2, sticky="ew", pady=6)

            record = {
                "canvas": canvas,
                "details": details,
                "label": detail_label,
                "name_label": name_label,
                "ratio": 0.0,
                "color": None,
                "classification": None,
                "renderer": RoundedBarRenderer(canvas),
            }
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
            record["canvas"].configure(
                background=palette.surface, height=self.appearance.pixels(16),
            )
            classification = record["classification"]
            color = (
                palette.classification(classification)
                if classification is not None
                else palette.foreground
            )
            record["label"].configure(foreground=color)
            record["color"] = color if classification else None
            self._draw_bar(record)

    def set_data(self, fingers, theme_name=None, max_deviation=None):
        """Display a mapping of finger names to FingerState values."""
        if theme_name is not None and theme_name != self.theme_name:
            self.set_theme(theme_name)
        if max_deviation is not None:
            self.max_deviation = max(float(max_deviation), 0.001)

        palette = self.palette
        for name, record in self._rows.items():
            finger = fingers.get(name) if fingers else None
            if finger is None:
                record["details"].set(self.layout.detail_text(None))
                record["label"].configure(
                    foreground=palette.foreground
                )
                record["ratio"] = 0.0
                record["color"] = None
                record["classification"] = None
            else:
                classification = finger.position.value
                color = palette.classification(classification)
                record["details"].set(self.layout.detail_text(finger))
                record["label"].configure(foreground=color)
                record["ratio"] = min(
                    max(finger.deviation / self.max_deviation, 0.0), 1.0
                )
                record["color"] = color
                record["classification"] = classification
            self._draw_bar(record)

    def _draw_bar(self, record):
        canvas = record["canvas"]
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        thickness = min(self.appearance.pixels(self.layout.bar_thickness), height - 2)
        top = (height - thickness) / 2
        record["renderer"].progress(
            (1, top, width - 1, top + thickness),
            record["ratio"], record["color"], self.palette.track,
        )
