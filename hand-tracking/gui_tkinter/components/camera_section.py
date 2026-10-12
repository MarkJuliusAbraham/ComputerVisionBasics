"""Shared camera selection and connection status for the application hub."""

import tkinter as tk
from tkinter import font as tkfont, ttk

from gui_tkinter.core.state import CameraState


class CameraSection(ttk.LabelFrame):
    """Keep camera controls aligned and reflect the capture worker's status."""

    def __init__(self, master, camera_index=0, on_switch=None):
        super().__init__(master, text="Camera", padding=(12, 10, 12, 10))
        self._on_switch = on_switch
        self.camera_state = CameraState(requested_index=camera_index)
        self._devices = {f"Camera {index}": index for index in range(10)}
        self._ensure_device(camera_index)
        self.columnconfigure(1, weight=1)

        self.selected_device = tk.StringVar(self, value=f"Camera {camera_index}")
        self.active_device = tk.StringVar(self, value="None")
        self.connection = tk.StringVar(self, value="Connecting")
        self.message = tk.StringVar(self, value=f"Opening camera {camera_index}…")

        ttk.Label(self, text="Device").grid(
            row=0, column=0, sticky="w", padx=(0, 12)
        )
        self.device_picker = ttk.Combobox(
            self, textvariable=self.selected_device, values=tuple(self._devices),
            state="readonly", width=18,
        )
        self.device_picker.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        self.switch_button = ttk.Button(
            self, text="Switch", width=10, command=self.switch_camera,
        )
        self.switch_button.grid(row=0, column=2, sticky="e")

        ttk.Label(self, text="Active").grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=(10, 0)
        )
        ttk.Label(self, textvariable=self.active_device, width=18).grid(
            row=1, column=1, sticky="w", pady=(10, 0)
        )
        ttk.Label(self, textvariable=self.connection, width=12, anchor="e").grid(
            row=1, column=2, sticky="e", pady=(10, 0)
        )

        # A fixed two-line area prevents lengthy worker messages from changing
        # the width or pushing the live hand data down during a switch.
        self._message_area = ttk.Frame(self)
        self._message_area.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        self._message_area.grid_propagate(False)
        self._message_area.columnconfigure(0, weight=1)
        self._message_area.rowconfigure(0, weight=1)
        self.message_label = ttk.Label(
            self._message_area, textvariable=self.message,
            anchor="nw", justify="left", width=1, wraplength=1,
        )
        self.message_label.grid(row=0, column=0, sticky="nsew")
        self._message_area.bind("<Configure>", self._resize_message)
        self.bind("<<ThemeChanged>>", self._theme_changed)
        self.selected_device.trace_add("write", self._refresh_switch_state)
        self._reserve_message_height()
        self._refresh_switch_state()

    def _ensure_device(self, index):
        if index is not None:
            self._devices[f"Camera {index}"] = index

    def _refresh_switch_state(self, *_args):
        selected = self._devices.get(self.selected_device.get())
        can_switch = (
            self._on_switch is not None
            and not self.camera_state.is_switching
            and selected is not None
            and (not self.camera_state.is_active or selected != self.camera_state.active_index)
        )
        self.switch_button.state(["!disabled"] if can_switch else ["disabled"])
        self.device_picker.configure(
            state="disabled" if self.camera_state.is_switching else "readonly"
        )

    def switch_camera(self):
        """Queue the selected device on the existing capture worker."""
        index = self._devices.get(self.selected_device.get())
        if (
            self.camera_state.is_switching or self._on_switch is None or index is None
            or (self.camera_state.is_active and index == self.camera_state.active_index)
        ):
            return
        self.camera_state.begin_switch(index)
        self.connection.set("Switching" if self.camera_state.is_active else "Connecting")
        self.message.set(f"Opening camera {index}…")
        self._refresh_switch_state()
        self._on_switch(index)

    def update_state(self, state, requested, active, message=None):
        """Display opening, successful, failed, and restored-camera results."""
        self._ensure_device(requested)
        self._ensure_device(active)
        self.device_picker.configure(values=tuple(self._devices))
        if state in ("opening", "switching"):
            self.camera_state.begin_switch(requested)
            self.camera_state.active_index = active
            self.camera_state.is_active = active is not None
            self.selected_device.set(f"Camera {requested}")
            self.connection.set("Switching" if state == "switching" else "Connecting")
            self.message.set(message or f"Opening camera {requested}…")
        elif state == "ready":
            self.camera_state.mark_ready(active)
            self.camera_state.requested_index = requested
            self.selected_device.set(f"Camera {active}")
            self.connection.set("Ready")
            self.message.set(message or "Camera is streaming.")
        elif state == "failed":
            self.camera_state.mark_failed(active)
            self.camera_state.requested_index = requested
            self.selected_device.set(f"Camera {requested}")
            self.connection.set("Unavailable")
            self.message.set(message or f"Could not open camera {requested}. Select a device and try again.")
        self.active_device.set(f"Camera {active}" if active is not None else "None")
        self._refresh_switch_state()

    def _resize_message(self, event):
        self.message_label.configure(wraplength=max(1, event.width))

    def _reserve_message_height(self):
        font_spec = ttk.Style(self).lookup("TLabel", "font") or "TkDefaultFont"
        font = tkfont.Font(root=self, font=font_spec)
        self._message_area.configure(height=2 * font.metrics("linespace") + 4)

    def _theme_changed(self, _event):
        self.after_idle(self._reserve_message_height)
