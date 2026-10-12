"""Independent sections that make up the settings form."""

from dataclasses import dataclass
import tkinter as tk
from tkinter import filedialog, ttk

from gui_tkinter.components.finger_threshold_control import FingerThresholdControl
from gui_tkinter.settings_panel.deviation_preview import DeviationPreview
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
    """Tracking switches, thresholds, and the live deviation preview."""

    FINGER_THRESHOLD_KEYS = (
        "finger_straight_threshold",
        "finger_curled_threshold",
        "finger_closed_threshold",
    )

    def __init__(self, master, theme_name, max_deviation, on_change=None):
        fields = (
            FieldSpec("track_hands", "Track hands", "check"),
            FieldSpec("profile", "Print FPS to console", "check"),
            FieldSpec(
                "pinch_distance_threshold", "Pinch distance threshold", "number",
                minimum=0.01, maximum=0.20, increment=0.01,
            ),
            FieldSpec(
                "pinch_release_factor", "Pinch release factor", "number",
                minimum=1.0, maximum=2.0, increment=0.05,
            ),
        )
        super().__init__(master, "Tracking options", fields, on_change)
        self._segment_count = 4
        self._max_deviation = max_deviation
        self.error = tk.StringVar()

        ttk.Label(self, text="Finger deviation ranges").pack(
            anchor="w", pady=(12, 2)
        )
        self.threshold_variables = {
            key: tk.DoubleVar() for key in self.FINGER_THRESHOLD_KEYS
        }
        self.variables.update(self.threshold_variables)
        self.finger_threshold_control = FingerThresholdControl(
            self,
            self.threshold_variables["finger_straight_threshold"],
            self.threshold_variables["finger_curled_threshold"],
            self.threshold_variables["finger_closed_threshold"],
            on_change=self._thresholds_changed,
        )
        self.finger_threshold_control.pack(fill="x", pady=(0, 6))

        self.preview = DeviationPreview(
            self, theme_name=theme_name, max_deviation=max_deviation
        )
        self.preview.pack(fill="x")

        ttk.Label(self, textvariable=self.error, wraplength=300).pack(
            anchor="w", pady=(8, 0)
        )

    def _thresholds_changed(self):
        self._update_preview_thresholds()
        self._notify_change()

    def _update_preview_thresholds(self):
        thresholds = self.thresholds
        if thresholds:
            self._max_deviation = thresholds[-1]
        self.preview.set_thresholds(
            thresholds,
            self._segment_count,
            self._max_deviation,
        )

    @property
    def thresholds(self):
        return [
            self.threshold_variables[key].get()
            for key in self.FINGER_THRESHOLD_KEYS
        ]

    @property
    def tracking_preview_active(self):
        return self.preview.visible

    def values(self):
        values = super().values()
        values["finger_classification_thresholds"] = self.thresholds
        values["finger_segment_count"] = self._segment_count
        return values

    def load(self, data):
        self.load_values({
            "track_hands": data.track_hands,
            "profile": data.profile,
            "pinch_distance_threshold": None,
            "pinch_release_factor": None,
        })
        for key, value in zip(self.FINGER_THRESHOLD_KEYS, data.finger_classification_thresholds):
            self.threshold_variables[key].set(value)
        self._segment_count = data.finger_segment_count
        self._max_deviation = data.finger_classification_thresholds[-1]
        self._update_preview_thresholds()
        self.error.set("")

    def set_theme(self, theme_name):
        self.finger_threshold_control.set_theme(theme_name)
        self.preview.set_theme(theme_name)

    def set_preview_data(self, fingers, status):
        self.preview.set_data(fingers, status)

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
