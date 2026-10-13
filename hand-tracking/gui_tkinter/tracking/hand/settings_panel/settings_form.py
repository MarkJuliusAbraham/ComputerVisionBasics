"""Hand tracking settings form with a dedicated deviation preview."""

from gui_tkinter.settings_panel.sectioned_form import SectionedSettingsForm

from .tracking_section import TrackingSection
from .landmarker_model_section import LandmarkerModelSection
from .optimistic_section import OptimisticTrackingSection
from gui_tkinter.components.theme import ThemeMetrics


class HandSettingsForm(SectionedSettingsForm):
    def __init__(self, master, *, settings, on_change=None, on_settings_path=None, model_asset=None):
        super().__init__(master, on_change)
        self.appearance = ThemeMetrics(self)
        self.content.columnconfigure(0, weight=1, uniform="hand_settings")
        self.content.columnconfigure(1, weight=1, uniform="hand_settings")
        self.model = LandmarkerModelSection(self.content, on_change=self.notify_change, asset=model_asset)
        self.add_section("Landmarker Model", self.model, row=0, column=0)
        self.tracking = TrackingSection(
            self.content, settings.data.theme,
            settings.data.finger_classification_thresholds[-1],
            on_change=self.notify_change,
        )
        self.add_section("Tracking", self.tracking, row=1, column=0)
        self.optimistic = OptimisticTrackingSection(
            self.content, on_change=self.notify_change, appearance=self.appearance,
        )
        self.add_section("Optimistic Tracking", self.optimistic, row=0, column=1, rowspan=2)
        self.bind("<<ThemeChanged>>", lambda _event: self.after_idle(self._refresh_layout))
        self._refresh_layout()

    def _refresh_layout(self):
        self.appearance.refresh()
        pixels = self.appearance.pixels
        self.model.grid_configure(padx=(0, pixels(16)), pady=(0, pixels(16)))
        self.tracking.grid_configure(padx=(0, pixels(16)))

    @property
    def tracking_preview_active(self):
        return self.tracking.deviation.preview.visible

    def set_preview_data(self, fingers, status):
        self.tracking.deviation.preview.set_data(fingers, status)
