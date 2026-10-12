from tkinter import ttk

from .live_gesture_section import LiveGestureSection


class HandDebugTab(ttk.Frame):
    """Hand tracking actions and live diagnostics."""

    def __init__(
        self,
        master,
        on_restart,
        on_close,
        on_toggle_tracking=None,
        theme_name="Light",
        max_deviation=75.0,
    ):
        super().__init__(master)
        self.on_toggle_tracking = on_toggle_tracking

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=20, pady=(14, 2))
        ttk.Button(actions, text="Restart tracking", command=on_restart).pack(
            side="left", fill="x", expand=True, padx=(0, 4)
        )
        ttk.Button(actions, text="Close window", command=on_close).pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )

        pause_row = ttk.Frame(self)
        pause_row.pack(fill="x", padx=20, pady=(2, 4))
        self.pause_tracking_button = ttk.Button(
            pause_row, text="Pause tracking", command=self._toggle_tracking,
            width=24,
        )
        self.pause_tracking_button.pack(anchor="center", pady=(0, 4))

        self.live_gestures = LiveGestureSection(
            self, theme_name=theme_name, max_deviation=max_deviation,
        )
        self.live_gestures.pack(fill="both", expand=True, padx=20, pady=(8, 16))

    def _toggle_tracking(self):
        if self.on_toggle_tracking:
            self.on_toggle_tracking()

    def set_tracking_paused(self, paused):
        self.pause_tracking_button.configure(
            text="Resume tracking" if paused else "Pause tracking"
        )
