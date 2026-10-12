"""Independent sections that make up the settings form."""

from dataclasses import dataclass
import tkinter as tk
from tkinter import filedialog, ttk

from gui_tkinter.settings_panel.deviation_settings import DeviationSettings
from settings.settings_manager import Settings, THEMES, UI_SCALES


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    kind: str
    options: tuple[str, ...] = ()
    minimum: float = 0.0
    maximum: float = 0.0
    increment: float = 1.0


class _FieldSection(ttk.LabelFrame):
    """Label frame that builds consistently aligned ttk form rows."""

    def __init__(self, master, title, fields, on_change=None):
        super().__init__(master, text=title, padding=(12, 8, 12, 10))
        self.variables = {}
        self._on_change = on_change
        self.columnconfigure(0, weight=1)
        for field in fields:
            self._add_field(field)

    def _add_field(self, field):
        row = ttk.Frame(self)
        row.pack(fill="x", pady=4)
        row.columnconfigure(0, weight=1)

        if field.kind == "check":
            variable = tk.BooleanVar()
            ttk.Checkbutton(
                row,
                text=field.label,
                variable=variable,
            ).grid(row=0, column=0, sticky="w")
        elif field.kind == "number":
            variable = tk.DoubleVar()
            ttk.Label(row, text=field.label).grid(
                row=0, column=0, sticky="w", padx=(0, 12)
            )
            ttk.Spinbox(
                row,
                textvariable=variable,
                from_=field.minimum,
                to=field.maximum,
                increment=field.increment,
                width=9,
                command=self._notify_change,
            ).grid(row=0, column=1, sticky="e")
        else:
            variable = tk.StringVar()
            ttk.Label(row, text=field.label).grid(
                row=0, column=0, sticky="w", padx=(0, 12)
            )
            combo = ttk.Combobox(
                row,
                textvariable=variable,
                values=field.options,
                state="readonly",
                width=14,
            )
            combo.grid(row=0, column=1, sticky="e")
            combo.bind("<<ComboboxSelected>>", lambda _event: self._notify_change())

        variable.trace_add("write", lambda *_args: self._notify_change())
        self.variables[field.key] = variable

    def _notify_change(self):
        if self._on_change:
            self._on_change()

    def values(self):
        return {key: variable.get() for key, variable in self.variables.items()}

    def load_values(self, values):
        for key, variable in self.variables.items():
            if key in values and values[key] is not None:
                variable.set(values[key])


class TrackingSection(_FieldSection):
    """Tracking switches and the editable deviation settings."""

    def __init__(self, master, theme_name, max_deviation, on_change=None):
        fields = (
            FieldSpec("track_hands", "Track hands", "check"),
            FieldSpec("profile", "Print FPS to console", "check"),
        )
        super().__init__(master, "Tracking options", fields, on_change)
        self.error = tk.StringVar(self)
        self.deviation = DeviationSettings(
            self, theme_name=theme_name, max_deviation=max_deviation,
            on_change=self._notify_change,
        )
        self.deviation.pack(fill="x")
        self.variables.update(self.deviation.variables)
        ttk.Label(self, textvariable=self.error, wraplength=300).pack(
            anchor="w", pady=(8, 0)
        )

    @property
    def finger_threshold_control(self):
        return self.deviation.control

    @property
    def thresholds(self):
        return self.deviation.control.thresholds

    @property
    def tracking_preview_active(self):
        return self.deviation.preview.visible

    def values(self):
        values = super().values()
        values.update(self.deviation.values())
        return values

    def load(self, data):
        self.load_values({"track_hands": data.track_hands, "profile": data.profile})
        self.deviation.load(data)
        self.error.set("")

    def set_theme(self, theme_name):
        self.deviation.set_theme(theme_name)

    def set_preview_data(self, fingers, status):
        self.deviation.preview.set_data(fingers, status)

    def set_error(self, message):
        self.error.set(message)


class AppearanceSection(_FieldSection):
    """Theme and UI scale preferences."""

    def __init__(self, master, on_change=None):
        fields = (
            FieldSpec("theme", "Theme", "choice", options=THEMES),
            FieldSpec("ui_scale", "UI scale", "choice", options=UI_SCALES),
        )
        super().__init__(master, "Appearance options", fields, on_change)

    def load(self, data):
        self.load_values({"theme": data.theme, "ui_scale": data.ui_scale})


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
        self.path.set(path)
        self.status.set("Settings file selected")
        if self._on_path:
            self._on_path(path)

    def load(self, path):
        self.path.set(path)

    def set_status(self, message):
        self.status.set(message)
