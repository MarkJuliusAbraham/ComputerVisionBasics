"""Hand tracking settings form with a dedicated deviation preview."""

from gui_tkinter.settings_panel.sectioned_form import SectionedSettingsForm

from .tracking_section import TrackingSection


class HandSettingsForm(SectionedSettingsForm):
    def __init__(self, master, *, settings, on_change=None, on_settings_path=None):
        super().__init__(master, on_change)
        self.tracking = TrackingSection(
            self.scroll.content, settings.data.theme,
            settings.data.finger_classification_thresholds[-1],
            on_change=self.notify_change,
        )
        self.add_section("Tracking", self.tracking)

    @property
    def tracking_preview_active(self):
        return self.tracking.deviation.preview.visible

    def set_preview_data(self, fingers, status):
        self.tracking.deviation.preview.set_data(fingers, status)
