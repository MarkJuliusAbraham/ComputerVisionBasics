"""Show the actual loaded model and an actionable, theme-aware warning."""

import tkinter as tk
from tkinter import ttk

from hand_tracking.frontend.components.status_message import StatusMessage
from hand_tracking.backend.landmarker.model_asset import HandLandmarkerAsset
from hand_tracking.backend.landmarker.model_status import ModelCondition, ModelStatus


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
        condition = status.condition
        if condition == ModelCondition.LOADING:
            message = "Loading selected model… Hand detection will resume when it is ready."
        elif condition == ModelCondition.FAILED:
            message = (
                "Selected model could not load. " + ("Keeping the current model. " if status.available else "")
                + "Go to Settings → Landmarker Model to choose a compatible bundle."
            )
        elif condition == ModelCondition.MISSING:
            message = "No model is in use. Go to Settings → Landmarker Model to select one."
        else:
            message = f"{HandLandmarkerAsset.family} · Ready"
        self.message.set(message, warning=status.needs_attention)
