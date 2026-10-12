import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.deviation_bar import DeviationBar
from gui_tkinter.core.state import CameraState


class MainTab(ttk.Frame):
    """Main page controls and live hand diagnostics."""

    def __init__(
        self,
        master,
        on_restart,
        on_close,
        camera_index=0,
        on_camera_switch=None,
        on_toggle_tracking=None,
        theme_name="Light",
        max_deviation=75.0,
    ):
        super().__init__(master)
        self.on_camera_switch = on_camera_switch
        self.on_toggle_tracking = on_toggle_tracking
        self.camera_state = CameraState(requested_index=camera_index)
        self._theme_name = theme_name
        self._max_deviation = max_deviation
        self._latest_preview_fingers = None
        self._preview_tracking_state = "No hand detected"
        self.gesture_display = {}

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=20, pady=(14, 2))
        ttk.Button(actions, text="Restart", command=on_restart).pack(
            side="left", fill="x", expand=True, padx=(0, 4)
        )
        ttk.Button(actions, text="Exit", command=on_close).pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )

        pause_row = ttk.Frame(self)
        pause_row.pack(fill="x", padx=20, pady=(2, 4))
        self.pause_tracking_button = ttk.Button(
            pause_row, text="Pause tracking", command=self._toggle_tracking,
            width=24,
        )
        self.pause_tracking_button.pack(anchor="center", pady=(0, 4))

        camera_section = ttk.LabelFrame(self, text="Camera", padding=(12, 8, 12, 10))
        camera_section.pack(fill="x", padx=20, pady=(8, 8))
        camera_row = ttk.Frame(camera_section)
        camera_row.pack(fill="x")
        ttk.Label(camera_row, text="Device").pack(side="left")
        self.camera_var = tk.StringVar(value=str(camera_index))
        self.camera_picker = ttk.Combobox(
            camera_row,
            textvariable=self.camera_var,
            values=[str(index) for index in range(10)],
            state="readonly",
            width=8,
        )
        self.camera_picker.pack(side="left", padx=(8, 0))
        self.camera_switch_button = ttk.Button(
            camera_section, text="Switch", command=self.switch_camera,
            style="Accent.TButton",
        )
        self.camera_switch_button.pack(anchor="e", pady=(8, 0))
        self.camera_status = tk.StringVar(value="Current camera")
        ttk.Label(camera_section, textvariable=self.camera_status).pack(
            anchor="w", pady=(6, 0)
        )

        gesture_section = ttk.LabelFrame(
            self, text="Live gesture data", padding=(10, 6, 10, 8)
        )
        gesture_section.pack(fill="both", expand=True, padx=20, pady=(2, 14))
        self.gesture_enabled = tk.StringVar(value="Waiting for camera…")
        ttk.Label(
            gesture_section, textvariable=self.gesture_enabled, width=36
        ).pack(anchor="w", pady=(0, 5))
        hands_row = ttk.Frame(gesture_section)
        hands_row.pack(fill="both", expand=True)

        for column, handedness in enumerate(("Left", "Right")):
            self._build_hand_panel(hands_row, column, handedness)

    def _build_hand_panel(self, parent, column, handedness):
        panel = ttk.LabelFrame(
            parent, text=f"{handedness} hand", padding=(6, 4)
        )
        panel.grid(
            row=0, column=column, sticky="nsew",
            padx=(0 if column == 0 else 5, 0),
        )
        parent.columnconfigure(column, weight=1, uniform="hand")
        parent.rowconfigure(0, weight=1)

        values = {
            "palm": tk.StringVar(value="—"),
            "gesture": tk.StringVar(value="—"),
            "deviation_bar": None,
        }
        ttk.Label(panel, text="Palm").grid(row=0, column=0, sticky="w")
        ttk.Label(panel, textvariable=values["palm"], width=19).grid(
            row=0, column=1, columnspan=2, sticky="w"
        )
        ttk.Label(panel, text="Command").grid(row=1, column=0, sticky="w")
        ttk.Label(panel, textvariable=values["gesture"], width=19).grid(
            row=1, column=1, columnspan=2, sticky="w"
        )
        ttk.Separator(panel, orient="horizontal").grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=4
        )
        values["deviation_bar"] = DeviationBar(
            panel, theme_name=self._theme_name,
            max_deviation=self._max_deviation,
        )
        values["deviation_bar"].grid(
            row=3, column=0, columnspan=3, sticky="ew"
        )
        panel.columnconfigure(1, weight=1)
        self.gesture_display[handedness] = values

    def switch_camera(self):
        """Queue a camera change without blocking Tk's event loop."""
        if self.camera_state.is_switching:
            return
        try:
            index = int(self.camera_var.get())
        except ValueError:
            self.camera_status.set("Select a camera device")
            return
        if index == self.camera_state.active_index and self.camera_state.is_active:
            self.camera_status.set(f"Using camera {index}")
            return
        if not self.on_camera_switch:
            self.camera_status.set("Camera switching is unavailable")
            return
        self.camera_state.begin_switch(index)
        self.camera_switch_button.state(["disabled"])
        self.camera_status.set(f"Opening camera {index}…")
        self.on_camera_switch(index)

    def _toggle_tracking(self):
        if self.on_toggle_tracking:
            self.on_toggle_tracking()

    def set_tracking_paused(self, paused):
        self.pause_tracking_button.configure(
            text="Resume tracking" if paused else "Pause tracking"
        )

    def update_camera_state(self, state, requested, active, message=None):
        """Reflect the capture worker's latest status in the camera controls."""
        if state in ("opening", "switching"):
            self.camera_state.requested_index = requested
            self.camera_state.is_switching = True
            self.camera_switch_button.state(["disabled"])
            self.camera_status.set(f"Opening camera {requested}…")
        elif state == "ready":
            self.camera_state.mark_ready(active)
            self.camera_switch_button.state(["!disabled"])
            self.camera_var.set(str(active))
            self.camera_status.set(message or f"Using camera {active}")
        elif state == "failed":
            self.camera_state.mark_failed(active)
            self.camera_switch_button.state(["!disabled"])
            if active is not None:
                self.camera_var.set(str(active))
            self.camera_status.set(message or f"Could not open camera {requested}")

    def update_gesture_display(self, hand_states, enabled=True, paused=False):
        """Render the latest classified hand data and retain preview data."""
        if not enabled:
            self.gesture_enabled.set("Tracking disabled")
        elif paused:
            self.gesture_enabled.set("Tracking paused")
        elif not hand_states:
            self.gesture_enabled.set("No hands detected")
        else:
            self.gesture_enabled.set("Tracking active")

        preview_record = hand_states[0] if hand_states else None
        self._latest_preview_fingers = (
            preview_record["state"].fingers if preview_record else None
        )
        self._preview_tracking_state = (
            "Tracking disabled" if not enabled else
            "Tracking paused" if paused else
            "No hand detected" if preview_record is None else
            f"Live data · {preview_record['handedness']} hand"
        )

        for handedness, values in self.gesture_display.items():
            record = next(
                (item for item in hand_states if item["handedness"] == handedness),
                None,
            )
            if record is None:
                values["palm"].set("—")
                values["gesture"].set("—")
                values["deviation_bar"].set_data(
                    None, self._theme_name, self._max_deviation
                )
                continue

            state = record["state"]
            values["palm"].set(state.palm.value.replace("_", " ").title())
            values["gesture"].set(record["command"] or "—")
            values["deviation_bar"].set_data(
                state.fingers, self._theme_name, self._max_deviation
            )

    def set_display(self, theme_name, max_deviation):
        self._theme_name = theme_name
        self._max_deviation = max_deviation
        for values in self.gesture_display.values():
            values["deviation_bar"].set_theme(theme_name)

    @property
    def preview_fingers(self):
        return self._latest_preview_fingers

    @property
    def preview_status(self):
        return self._preview_tracking_state
