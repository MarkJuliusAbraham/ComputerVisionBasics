"""Live tracking state and spacious per-hand diagnostic panels."""

import tkinter as tk
from tkinter import ttk

from .hand_data_panel import HandDataPanel


class LiveGestureSection(ttk.LabelFrame):
    """Display both hands while retaining live preview data for settings."""

    def __init__(self, master, theme_name="Light", max_deviation=75.0):
        super().__init__(master, text="Live gesture data", padding=(16, 14))
        self._preview_fingers = None
        self._preview_status = "No hand detected"
        self.tracking_status = tk.StringVar(self, value="Waiting for camera…")
        ttk.Label(self, textvariable=self.tracking_status, width=36).pack(
            anchor="w", pady=(0, 14)
        )

        hands = ttk.Frame(self)
        hands.pack(fill="both", expand=True)
        hands.rowconfigure(0, weight=1)
        self.hand_panels = {}
        for column, handedness in enumerate(("Left", "Right")):
            hands.columnconfigure(column, weight=1, uniform="hand")
            panel = HandDataPanel(
                hands, handedness, theme_name=theme_name, max_deviation=max_deviation,
            )
            panel.grid(
                row=0, column=column, sticky="nsew",
                padx=(0, 10) if column == 0 else (10, 0),
            )
            self.hand_panels[handedness] = panel

    def update_data(self, hand_states, enabled=True, paused=False):
        if not enabled:
            self.tracking_status.set("Tracking disabled")
        elif paused:
            self.tracking_status.set("Tracking paused")
        else:
            self.tracking_status.set("Tracking active")

        preview = hand_states[0] if hand_states else None
        self._preview_fingers = preview["state"].fingers if preview else None
        self._preview_status = (
            "Tracking disabled" if not enabled else
            "Tracking paused" if paused else
            "No hand detected" if preview is None else
            f"Live data · {preview['handedness']} hand"
        )
        by_hand = {record["handedness"]: record for record in hand_states}
        for handedness, panel in self.hand_panels.items():
            panel.set_data(by_hand.get(handedness))

    def set_display(self, theme_name, max_deviation):
        for panel in self.hand_panels.values():
            panel.set_display(theme_name, max_deviation)

    @property
    def preview_fingers(self):
        return self._preview_fingers

    @property
    def preview_status(self):
        return self._preview_status
