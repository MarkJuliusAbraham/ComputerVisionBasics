import tkinter as tk
from tkinter import ttk

from .theme import (
    gesture_bar_background,
    gesture_classification_color,
)


class DeviationBar(ttk.Frame):
    """Three-column finger deviation table with proportional color bars."""

    FINGERS = ("thumb", "index", "middle", "ring", "pinky")
    def __init__(self, master, fingers=None, theme_name="Light", max_deviation=75.0, **kwargs):
        super().__init__(master, **kwargs)
        self.theme_name = theme_name
        self.max_deviation = max(float(max_deviation), 0.001)
        self._rows = {}
        self.columnconfigure(1, weight=1, minsize=120)

        ttk.Label(self, text="Finger", anchor="w").grid(
            row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 10)
        )
        ttk.Label(self, text="Deviation", anchor="center", justify="center").grid(
            row=0, column=1, sticky="ew", pady=(0, 10)
        )
        ttk.Label(self, text="Score / class", anchor="e").grid(
            row=0, column=2, sticky="e", padx=(12, 0), pady=(0, 10)
        )

        for row, name in enumerate(self.FINGERS, start=1):
            # Reserve two lines in every state so receiving data does not
            # change row heights or make the hand panels jump.
            details = tk.StringVar(self, value="—\n—")
            canvas = tk.Canvas(
                self, height=16, width=120, highlightthickness=0, borderwidth=0
            )
            detail_label = ttk.Label(
                self, textvariable=details, width=13, anchor="e", justify="right"
            )
            ttk.Label(self, text=name.title(), width=8, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=6
            )
            canvas.grid(row=row, column=1, sticky="ew", pady=6)
            detail_label.grid(row=row, column=2, sticky="e", padx=(12, 0), pady=6)

            record = {
                "canvas": canvas,
                "details": details,
                "label": detail_label,
                "ratio": 0.0,
                "color": None,
                "classification": None,
            }
            self._rows[name] = record
            canvas.bind(
                "<Configure>",
                lambda event, item=record: self._draw_bar(item),
            )

        self.set_theme(theme_name)
        self.set_data(fingers)

    def set_theme(self, theme_name):
        """Apply the theme's trough and classification colors to every row."""
        self.theme_name = theme_name
        trough = gesture_bar_background(theme_name)
        for record in self._rows.values():
            record["canvas"].configure(background=trough)
            classification = record["classification"]
            color = (
                gesture_classification_color(theme_name, classification)
                if classification is not None
                else ttk.Style(self).lookup("TLabel", "foreground")
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

        for name, record in self._rows.items():
            finger = fingers.get(name) if fingers else None
            if finger is None:
                record["details"].set("—\n—")
                record["label"].configure(
                    foreground=ttk.Style(self).lookup("TLabel", "foreground")
                )
                record["ratio"] = 0.0
                record["color"] = None
                record["classification"] = None
            else:
                classification = getattr(
                    finger.position, "semantic_class", finger.position.value
                )
                label = getattr(
                    finger.position, "label", finger.position.value.replace("_", " ").title()
                )
                color = gesture_classification_color(self.theme_name, classification)
                record["details"].set(
                    f"{finger.deviation:.1f}°\n{label}"
                )
                record["label"].configure(foreground=color)
                record["ratio"] = min(
                    max(finger.deviation / self.max_deviation, 0.0), 1.0
                )
                record["color"] = color
                record["classification"] = classification
            self._draw_bar(record)

    @staticmethod
    def _draw_bar(record):
        canvas = record["canvas"]
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        fill_width = int(width * record["ratio"])
        color = record["color"]
        if color and 0 < fill_width and width > 1 and height > 1:
            canvas.create_rectangle(
                0, 0, fill_width, height, fill=color, outline=""
            )
