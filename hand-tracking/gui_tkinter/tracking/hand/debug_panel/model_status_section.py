"""Show the actual loaded model and an actionable, theme-aware warning."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.status_message import StatusMessage
from landmarker import HandLandmarkerAsset, ModelStatus


class ModelStatusSection(ttk.LabelFrame):
    def __init__(self, master, on_open_settings=None, *, appearance=None):
        super().__init__(master, text="Landmarker Model", padding=(12, 8))
        self._status = ModelStatus()
        self.name = tk.StringVar(self)
        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, textvariable=self.name, width=1, anchor="w").pack(
            side="left", fill="x", expand=True,
        )
        ttk.Button(header, text="Model settings…", command=on_open_settings).pack(
            side="right", padx=(12, 0),
        )
        self.message = StatusMessage(self, appearance=appearance)
        self.message.pack(fill="x", pady=(6, 0))
        self.set_status(self._status)

    def set_status(self, status):
        self._status = status
        self.name.set(status.name)
        if status.phase == "loading":
            message = "Loading selected model… Hand detection will resume when it is ready."
        elif status.phase == "failed":
            message = (
                "Selected model could not load. " + ("Keeping the current model. " if status.available else "")
                + "Go to Settings → Landmarker Model to choose a compatible bundle."
            )
        elif not status.available:
            message = "No model is in use. Go to Settings → Landmarker Model to select one."
        else:
            message = f"{HandLandmarkerAsset.family} · Ready"
        warning = self._status.phase == "failed" or not self._status.available
        self.message.set(message, warning=warning)
