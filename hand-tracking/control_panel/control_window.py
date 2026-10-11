import tkinter as tk
from tkinter import filedialog, font, ttk

from control_panel.theme import apply_theme, resolve_scale
from control_panel.unapplied_changes_dialog import UnappliedChangesDialog
from settings.settings_manager import Settings, SettingsData, THEMES, UI_SCALES

BASE_SIZE = (440, 420)  # window size in pixels at 100%

# Each section: (title, [(key, label, options)]).
# options=None shows a checkbox; a tuple of choices shows a dropdown.
SETTINGS_SECTIONS = [
    ("Tracking", [
        ("track_hands", "Track hands", None),
        ("profile", "Print FPS to console", None),
    ]),
    ("Appearance", [
        ("theme", "Theme", THEMES),
        ("ui_scale", "UI scale", UI_SCALES),
    ]),
]
class ControlWindow:
    """Control panel with Main and Settings tabs."""

    def __init__(
        self,
        on_restart,
        on_close,
        settings,
        on_settings_path=None,
        on_apply=None,
    ):
        self.on_settings_path = on_settings_path
        self.on_apply = on_apply
        self._baseline = SettingsData()

        self.root = tk.Tk()
        self.root.title("Controls")
        self.root.resizable(False, False)
        self._scale = None  # last applied scale, set by _apply_display

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        main_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.advanced_tab = ttk.Frame(self.notebook)
        self.notebook.add(main_tab, text="Main")
        self.notebook.add(self.settings_tab, text="Settings")
        self.notebook.add(self.advanced_tab, text="Advanced")
        settings_tab = self.settings_tab

        # Main tab
        ttk.Button(main_tab, text="Restart", command=on_restart).pack(
            padx=20, pady=(20, 5), fill="x"
        )
        ttk.Button(main_tab, text="Exit", command=on_close).pack(
            padx=20, pady=5, fill="x"
        )

        # Settings tab: Apply button, bottom-right (packed first so it stays at the bottom)
        button_row = ttk.Frame(settings_tab)
        button_row.pack(side="bottom", fill="x", padx=20, pady=15)
        self.apply_button = ttk.Button(
            button_row, text="Apply", command=self.apply, style="Accent.TButton"
        )
        self.apply_button.pack(side="right")

        # One labelled section per group of related settings
        self.vars = {}
        for title, items in SETTINGS_SECTIONS:
            section = ttk.LabelFrame(
                settings_tab, text=title, padding=(12, 6, 12, 10)
            )
            section.pack(fill="x", padx=20, pady=(0, 10))

            for key, label, options in items:
                if options is None:
                    var = tk.BooleanVar()
                    ttk.Checkbutton(
                        section,
                        text=label,
                        variable=var,
                        command=self._refresh_apply_state,
                    ).pack(anchor="w", pady=2)
                else:
                    var = tk.StringVar()
                    option_row = ttk.Frame(section)
                    option_row.pack(fill="x", pady=2)
                    ttk.Label(option_row, text=label).pack(side="left")
                    combo = ttk.Combobox(
                        option_row,
                        textvariable=var,
                        values=options,
                        state="readonly",
                        width=12,
                    )
                    combo.pack(side="left", padx=(8, 0))
                    combo.bind(
                        "<<ComboboxSelected>>",
                        lambda e: self._refresh_apply_state(),
                    )
                self.vars[key] = var

        file_section = ttk.LabelFrame(self.advanced_tab, text="Settings file", padding=(12, 6, 12, 10))
        file_section.pack(fill="x", padx=20, pady=20)
        row = ttk.Frame(file_section)
        row.pack(fill="x")
        self.path_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.path_var, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse...", command=self.browse).pack(side="left", padx=(8, 0))
        self.status_var = tk.StringVar()
        ttk.Label(file_section, textvariable=self.status_var).pack(anchor="w", pady=(6, 0))
        self.show_settings(settings)
        self.status_var.set("Settings file loaded")

        # Watch tab switches so we can guard the Settings tab
        self._current_tab = self.notebook.select()
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.root.protocol("WM_DELETE_WINDOW", on_close)

    # ---- pending-change tracking ----

    def get_values(self):
        """Current widget values, as a dict of key -> value."""
        return SettingsData.from_dict({key: var.get() for key, var in self.vars.items()})

    def is_dirty(self):
        return self.get_values() != self._baseline

    def _refresh_apply_state(self):
        """Grey out Apply unless something differs from the baseline."""
        if self.is_dirty():
            self.apply_button.state(["!disabled"])
        else:
            self.apply_button.state(["disabled"])

    def show_settings(self, settings):
        """Refresh the path field and all widgets from a Settings object."""
        self.path_var.set(settings.path)
        for key, var in self.vars.items():
            value = getattr(settings.data, key)
            var.set(bool(value) if isinstance(var, tk.BooleanVar) else value)
        self._apply_display(settings.data.theme, settings.data.ui_scale)
        self._baseline = self.get_values()  # whatever is shown now is the baseline
        self._refresh_apply_state()

    def apply(self):
        values = self.get_values()
        if self.on_apply:
            self.on_apply(values)
        self._apply_display(values.theme, values.ui_scale)
        self._baseline = values
        self._refresh_apply_state()
        self.status_var.set("Settings applied and saved")

    def discard(self):
        """Revert the widgets to the baseline."""
        for key, var in self.vars.items():
            var.set(getattr(self._baseline, key))
        self._refresh_apply_state()

    # ---- leaving the Settings tab ----

    def _on_tab_changed(self, event):
        old_tab = self._current_tab
        new_tab = self.notebook.select()
        self._current_tab = new_tab

        leaving_settings = old_tab == str(self.settings_tab) and new_tab != old_tab
        if leaving_settings and self.is_dirty():
            if not self._confirm_leave():
                # Cancel: go back to the Settings tab
                self._current_tab = old_tab
                self.notebook.select(old_tab)

    def _confirm_leave(self):
        """Ask what to do with pending changes. Returns False if the user cancels."""
        choice = UnappliedChangesDialog(self.root).show()
        if choice == "cancel":
            return False
        if choice == "apply":
            self.apply()
        else:
            self.discard()
        return True

    # ---- file browsing ----

    def browse(self):
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Select settings file",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:  # user cancelled
            return

        if not Settings.is_valid_path(path):
            self.status_var.set("Invalid: must be an existing .json file")
            return

        self.status_var.set("Settings file selected")
        if self.on_settings_path:
            self.on_settings_path(path)  # Application reloads and refreshes us

    def update(self):
        self.root.update()

    def close(self):
        self.root.destroy()

    def _apply_display(self, theme, ui_scale):
        """Apply theme and UI scale; resize the window only if the scale changed."""
        scale = resolve_scale(self.root, ui_scale)
        apply_theme(self.root, theme, scale)
        if scale != self._scale:
            self._scale = scale
            self.root.geometry(
                f"{int(BASE_SIZE[0] * scale)}x{int(BASE_SIZE[1] * scale)}"
            )
