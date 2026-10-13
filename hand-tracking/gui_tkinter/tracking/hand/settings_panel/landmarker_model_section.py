"""Scoped model selection, using the backend's shared compatibility policy."""

import tkinter as tk
from tkinter import filedialog, ttk

from gui_tkinter.components.status_message import StatusMessage
from landmarker import HandLandmarkerAsset
from gui_tkinter.core.change_notifications import ChangeNotifications


class LandmarkerModelSection(ttk.LabelFrame):
    def __init__(self, master, on_change=None, *, asset=None):
        super().__init__(master, text="Landmarker Model", padding=(12, 8, 12, 10))
        self.asset = asset if asset is not None else HandLandmarkerAsset()
        self.changes = ChangeNotifications(self, on_change)
        self.path = tk.StringVar(self)
        self.variables = {"hand_landmarker_model_path": self.path}
        self._saved_path = ""
        self._runtime_status = None

        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.path, state="readonly", width=1).pack(
            side="left", fill="x", expand=True,
        )
        ttk.Button(row, text="Browse…", command=self.browse).pack(side="left", padx=(8, 0))
        ttk.Button(row, text="Clear", command=self.clear).pack(side="left", padx=(8, 0))
        self.feedback = StatusMessage(self)
        self.feedback.pack(fill="x", pady=(8, 0))
        self._set_message("Compatible MediaPipe Hand Landmarker .task bundles only.")
        self.changes.watch(self.path)

    def browse(self):
        options = {}
        if self.path.get():
            try:
                options["initialdir"] = str(self.asset.resolve(self.path.get()).parent)
            except (OSError, ValueError, RuntimeError):
                pass  # Browsing must still work when a saved path is malformed.
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(), title="Select Hand Landmarker model",
            filetypes=[("MediaPipe Hand Landmarker bundles", "*.task")], **options,
        )
        if not path:
            return
        try:
            selected = self.asset.validate_path(path)
        except ValueError as error:
            self._set_message(str(error), invalid=True)
            return
        self.path.set(selected)
        self._set_message("Model selected. Apply to load it and save this choice.")

    def clear(self):
        self.path.set("")
        self._set_message("Apply to unload the model and disable hand detection.")

    def _set_message(self, message, invalid=False):
        self.feedback.set(message, warning=invalid)

    def values(self):
        return {"hand_landmarker_model_path": self.path.get()}

    def load(self, data):
        self._saved_path = data.hand_landmarker_model_path
        with self.changes.suspended():
            self.path.set(data.hand_landmarker_model_path)
        self._set_message("Compatible MediaPipe Hand Landmarker .task bundles only.")
        if self._runtime_status is not None:
            self.set_model_status(self._runtime_status)

    def set_model_status(self, status):
        self._runtime_status = status
        if self.path.get() != self._saved_path:
            return  # Preserve feedback about the user's uncommitted selection.
        if status.phase == "loading":
            self._set_message("Loading the selected model in the background…")
        elif status.phase == "failed":
            self._set_message(f"Could not load model: {status.message[:180]}", invalid=True)
        elif not status.available:
            self._set_message("No model loaded. Browse for a compatible .task bundle and click Apply.", invalid=True)
        else:
            self._set_message("Compatible MediaPipe Hand Landmarker model loaded.")
