"""Independent sections that make up the settings form."""

import tkinter as tk
from tkinter import filedialog, ttk

from settings.settings_manager import Settings, THEMES, UI_SCALES
from gui_tkinter.components.field_section import FieldSection, FieldSpec


class AppearanceSection(FieldSection):
    """Theme and UI scale preferences."""

    def __init__(self, master, on_change=None):
        fields = (
            FieldSpec("theme", "Theme", "choice", options=THEMES),
            FieldSpec("ui_scale", "UI scale", "choice", options=UI_SCALES),
        )
        super().__init__(master, "Appearance options", fields, on_change)

    def load(self, data):
        self.load_values({"theme": data.theme, "ui_scale": data.ui_scale})


class DiagnosticsSection(FieldSection):
    """Application-wide diagnostic logging."""

    def __init__(self, master, on_change=None):
        super().__init__(master, "Diagnostics", (
            FieldSpec("profile", "Print FPS and detection latency to console", "check"),
        ), on_change)

    def load(self, data):
        self.load_values({"profile": data.profile})


class AdvancedSection(ttk.LabelFrame):
    """Settings file selection and its status message."""

    def __init__(self, master, on_path=None):
        super().__init__(master, text="Settings file", padding=(12, 8, 12, 10))
        self._toplevel = self.winfo_toplevel()
        self._on_path = on_path
        self.path = tk.StringVar()
        self.status = tk.StringVar()

        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.path, state="readonly").pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(row, text="Browse...", command=self.browse).pack(
            side="left", padx=(6, 0)
        )
        ttk.Label(self, textvariable=self.status, wraplength=240).pack(
            anchor="w", pady=(8, 0)
        )

    def browse(self):
        path = filedialog.askopenfilename(
            parent=self._toplevel,
            title="Select settings file",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        if not Settings.is_valid_path(path):
            self.status.set("Invalid: must be an existing .json file")
            return
        if self._on_path and self._on_path(path) is False:
            return
        self.path.set(path)
        self.status.set("Settings file selected")

    def load(self, path):
        self.path.set(path)

    def set_status(self, message):
        self.status.set(message)
