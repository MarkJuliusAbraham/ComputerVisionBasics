"""Settings form assembly and delegation to individual sections."""

from tkinter import ttk

from gui_tkinter.components.scrollable_frame import ScrollableFrame
from gui_tkinter.settings_panel.sections import (
    AdvancedSection,
    AppearanceSection,
    TrackingSection,
)


class SettingsForm(ttk.Frame):
    """Build and expose the editable settings sections."""

    def __init__(
        self,
        master,
        *,
        theme_name,
        max_deviation,
        on_change=None,
        on_settings_path=None,
    ):
        super().__init__(master)
        self._on_change = on_change
        self._finger_deviation_calculation = "default"
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)

        self.sections = {}
        self.tracking = TrackingSection(
            self.scroll.content,
            theme_name=theme_name,
            max_deviation=max_deviation,
            on_change=on_change,
        )
        self.appearance = AppearanceSection(
            self.scroll.content, on_change=on_change
        )
        self.advanced = AdvancedSection(
            self.scroll.content, on_path=on_settings_path
        )
        self._add_section(
            "Tracking",
            "Hand tracking behavior and diagnostics",
            self.tracking,
        )
        self._add_section(
            "Appearance",
            "Choose the application theme and display scale",
            self.appearance,
        )
        self._add_section(
            "Advanced",
            "File and diagnostic options",
            self.advanced,
        )

        self.variables = {
            **self.tracking.variables,
            **self.appearance.variables,
        }
        self.path_var = self.advanced.path
        self.status_var = self.advanced.status
        self.tracking_error = self.tracking.error

    def _add_section(self, name, description, section):
        page = ttk.Frame(self.scroll.content, padding=(4, 4, 4, 8))
        page.pack(fill="x", expand=False)
        self.sections[name] = page
        ttk.Separator(page, orient="horizontal").pack(fill="x", pady=(0, 8))
        ttk.Label(
            page,
            text=name,
            anchor="w",
            font=("TkDefaultFont", 11, "bold"),
        ).pack(anchor="w")
        ttk.Label(page, text=description, justify="left", anchor="w").pack(
            anchor="w", fill="x", pady=(2, 8)
        )
        section.pack(fill="x", anchor="n")

    def values(self):
        values = {}
        values.update(self.tracking.values())
        values.update(self.appearance.values())
        # Keep this setting intact while it is not exposed as a separate
        # control in the restored Tkinter form.
        values["finger_deviation_calculation"] = (
            self._finger_deviation_calculation
        )
        return values

    def load(self, settings):
        self.tracking.load(settings.data)
        self.appearance.load(settings.data)
        self.advanced.load(settings.path)
        self._finger_deviation_calculation = (
            settings.data.finger_deviation_calculation
        )
        self.set_theme(settings.data.theme)
        self.tracking_error.set("")

    def load_data(self, data):
        """Restore editable values without changing the selected file path."""
        self.tracking.load(data)
        self.appearance.load(data)
        self._finger_deviation_calculation = data.finger_deviation_calculation
        self.set_theme(data.theme)
        self.tracking_error.set("")

    def set_theme(self, theme_name):
        self.tracking.set_theme(theme_name)
        self.scroll.set_surface()

    def set_preview_data(self, fingers, status):
        self.tracking.set_preview_data(fingers, status)

    @property
    def tracking_preview_active(self):
        return self.tracking.tracking_preview_active

    def show_section(self, name):
        section = self.sections.get(name)
        if section is not None:
            self.scroll.scroll_to(section)

    def browse(self):
        self.advanced.browse()
