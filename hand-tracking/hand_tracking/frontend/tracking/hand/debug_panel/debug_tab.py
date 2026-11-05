import tkinter as tk
from tkinter import ttk

from hand_tracking.backend.settings.overlay_settings import OVERLAY_CONTENTS, OVERLAY_SIZES

from hand_tracking.frontend.core.callbacks import Action

from .live_gesture_section import LiveGestureSection
from .model_status_section import ModelStatusSection


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
        on_open_settings=None,
        on_toggle_overlay: Action | None = None,
        on_overlay_options: Action | None = None,
        on_overlay_content=None,
        on_overlay_size=None,
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
        toggles = ttk.Frame(pause_row)
        toggles.pack(anchor="center", pady=(0, 4))
        self.pause_tracking_button = ttk.Button(
            toggles, text="Pause tracking", command=self._toggle_tracking,
            width=24,
        )
        self.pause_tracking_button.pack(side="left", padx=(0, 6))
        self.overlay_button = ttk.Button(
            toggles, text="Enable Overlay", command=on_toggle_overlay, width=24,
        )
        self.overlay_button.pack(side="left", padx=(6, 0))
        ttk.Button(
            toggles, text="Overlay settings…", command=on_overlay_options, width=24,
        ).pack(side="left", padx=(12, 0))
        # What the overlay shows; switching applies and saves immediately.
        choices = ttk.Frame(pause_row)
        choices.pack(anchor="center")
        ttk.Label(choices, text="Overlay shows").pack(side="left")
        self.overlay_content = tk.StringVar(self, value=OVERLAY_CONTENTS[0])
        ttk.Combobox(
            choices, textvariable=self.overlay_content, values=OVERLAY_CONTENTS, state="readonly", width=18,
        ).pack(side="left", padx=(6, 12))
        ttk.Label(choices, text="Size").pack(side="left")
        self.overlay_size = tk.StringVar(self, value=OVERLAY_SIZES[1])
        self.size_choice = ttk.Combobox(
            choices, textvariable=self.overlay_size, values=OVERLAY_SIZES, state="readonly", width=9,
        )
        self.size_choice.pack(side="left", padx=(6, 0))
        self._loading_choices = False
        self.overlay_content.trace_add("write", lambda *_: self._choice_made(on_overlay_content, self.overlay_content))
        self.overlay_size.trace_add("write", lambda *_: self._choice_made(on_overlay_size, self.overlay_size))

        self.model_status = ModelStatusSection(self, on_open_settings=on_open_settings)
        self.model_status.pack(fill="x", padx=20, pady=(8, 0))

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

    def _choice_made(self, callback, variable) -> None:
        if not self._loading_choices and callback is not None:
            callback(variable.get())
        self._update_size_state()

    def set_overlay_choices(self, content: str, size: str) -> None:
        self._loading_choices = True
        try:
            self.overlay_content.set(content)
            self.overlay_size.set(size)
        finally:
            self._loading_choices = False
        self._update_size_state()

    def _update_size_state(self) -> None:
        # Only the camera-and-stats overlay has a size choice.
        camera = self.overlay_content.get() == "Camera and stats"
        self.size_choice.state(["!disabled", "readonly"] if camera else ["disabled"])

    def set_overlay_enabled(self, enabled: bool) -> None:
        self.overlay_button.configure(
            text="Disable Overlay" if enabled else "Enable Overlay",
            style="Accent.TButton" if enabled else "TButton",
        )
