"""Coordinator for the Tkinter settings form."""

from tkinter import ttk

from gui_tkinter.components.theme import apply_theme, resolve_scale
from gui_tkinter.settings_panel.settings_form import SettingsForm
from settings.settings_manager import SettingsData


class SettingsPanel:
    """Coordinate settings persistence, validation, and section callbacks."""

    def __init__(self, on_settings_path=None, on_apply=None):
        self.on_settings_path = on_settings_path
        self.on_apply = on_apply
        self._baseline = SettingsData()
        self._segment_count = 4
        self._max_deviation = 75.0

    def build(self, parent, settings):
        self.settings_tab = parent
        self.root = parent.winfo_toplevel()

        self.settings_content = ttk.Frame(parent)
        self.settings_content.pack(fill="both", expand=True)

        button_row = ttk.Frame(self.settings_content)
        button_row.pack(side="bottom", fill="x", padx=12, pady=(12, 12))
        self.apply_button = ttk.Button(
            button_row,
            text="Apply",
            command=self.apply,
            style="Accent.TButton",
        )
        self.apply_button.pack(side="right")

        self.form = SettingsForm(
            self.settings_content,
            theme_name=settings.data.theme,
            max_deviation=settings.data.finger_classification_thresholds[-1],
            on_change=self._refresh_apply_state,
            on_settings_path=self.on_settings_path,
        )
        self.form.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        # Keep the panel's small public surface convenient for callers that
        # need to inspect a specific setting widget.
        self.vars = self.form.variables
        self.topic_pages = self.form.sections
        self.path_var = self.form.path_var
        self.status_var = self.form.status_var
        self.tracking_error = self.form.tracking_error
        self.finger_threshold_control = self.form.tracking.finger_threshold_control

        self.show_settings(settings)
        self.status_var.set("Settings file loaded")
        self.root.after_idle(self.root.focus_set)

    # ---- form state -------------------------------------------------

    def get_values(self):
        return SettingsData.from_dict(self.form.values())

    def is_dirty(self):
        return self.get_values() != self._baseline

    def _refresh_apply_state(self):
        if not hasattr(self, "apply_button"):
            return
        self.apply_button.state(
            ["!disabled" if self.is_dirty() else "disabled"]
        )

    def show_settings(self, settings):
        """Load a complete Settings object into the form and baseline."""
        self._max_deviation = settings.data.finger_classification_thresholds[-1]
        self._segment_count = settings.data.finger_segment_count
        self._apply_display(settings.data.theme, settings.data.ui_scale)
        self.form.load(settings)
        self._baseline = self.get_values()
        self._refresh_apply_state()

    def apply(self):
        values = self.get_values()
        if not values.has_valid_finger_thresholds():
            self.tracking_error.set(
                "Thresholds must be strictly increasing between 0° and 120°."
            )
            self.show_topic("Tracking")
            return

        self.tracking_error.set("")
        if self.on_apply:
            self.on_apply(values)
        self._max_deviation = values.finger_classification_thresholds[-1]
        self._segment_count = values.finger_segment_count
        self._apply_display(values.theme, values.ui_scale)
        self._baseline = values
        self._refresh_apply_state()
        self.status_var.set("Settings applied and saved")

    def discard(self):
        """Restore applied values without changing the selected file path."""
        self.form.load_data(self._baseline)
        self._segment_count = self._baseline.finger_segment_count
        self._max_deviation = self._baseline.finger_classification_thresholds[-1]
        self._refresh_apply_state()

    # ---- display and live preview ----------------------------------

    def _apply_display(self, theme, ui_scale):
        scale = resolve_scale(self.root, ui_scale)
        apply_theme(self.root, theme, scale)
        self._theme_name = theme
        self._scale = scale
        if hasattr(self, "form"):
            self.form.set_theme(theme)

    def apply_display(self, theme, ui_scale):
        self._apply_display(theme, ui_scale)

    @property
    def tracking_preview_active(self):
        return self.form.tracking_preview_active

    def set_preview_data(self, fingers, status):
        self.form.set_preview_data(fingers, status)

    # ---- shell and validation actions -------------------------------

    def browse(self):
        self.form.browse()

    def show_topic(self, topic):
        self.form.show_section(topic)
