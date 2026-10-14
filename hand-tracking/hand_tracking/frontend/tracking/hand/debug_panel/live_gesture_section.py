"""Live tracking state and spacious per-hand diagnostic panels."""

import tkinter as tk
from tkinter import ttk

from hand_tracking.backend.gestures.hand_landmarks import HANDEDNESS

from .hand_data_panel import HandDataPanel


class LiveGestureSection(ttk.LabelFrame):
    """Display both hands from the debugging panel's shared live report."""

    def __init__(
        self, master, theme_name="Light", max_deviation=75.0, *,
        compact=False, palette_provider=None,
    ):
        super().__init__(
            master, text="" if compact else "Live gesture data",
            padding=(4, 4) if compact else (16, 14),
        )
        self.compact = compact
        self.tracking_status = tk.StringVar(self, value="Waiting for camera…")
        ttk.Label(self, textvariable=self.tracking_status, width=36).pack(
            anchor="w", pady=(0, 6 if compact else 14)
        )

        hands = ttk.Frame(self)
        hands.pack(fill="both", expand=True)
        hands.rowconfigure(0, weight=1)
        self.hand_panels = {}
        for column, handedness in enumerate(HANDEDNESS):
            hands.columnconfigure(column, weight=1, uniform="hand")
            panel = HandDataPanel(
                hands, handedness, theme_name=theme_name, max_deviation=max_deviation,
                compact=compact, palette_provider=palette_provider,
            )
            panel.grid(
                row=0, column=column, sticky="nsew",
                padx=(0, 10) if column == 0 else (10, 0),
            )
            self.hand_panels[handedness] = panel

    def update_data(self, data):
        status = data.tracking_status
        if self.tracking_status.get() != status:
            self.tracking_status.set(status)
        by_hand = data.by_hand
        for handedness, panel in self.hand_panels.items():
            panel.set_data(by_hand.get(handedness))

    def set_display(self, theme_name, max_deviation):
        for panel in self.hand_panels.values():
            panel.set_display(theme_name, max_deviation)
