"""Hand tracking settings form with a dedicated deviation preview."""

from hand_tracking.frontend.core.scaled_layout import ScaledLayout
from hand_tracking.frontend.settings_panel.sectioned_form import SectionedSettingsForm

from .tracking_section import TrackingSection
from .landmarker_model_section import LandmarkerModelSection
from .optimistic_section import OptimisticTrackingSection
from hand_tracking.frontend.components.theme import ThemeMetrics


class HandSettingsForm(SectionedSettingsForm):
    def __init__(self, master, *, settings, on_change=None, on_settings_path=None, model_asset=None):
        super().__init__(master, on_change)
        self.appearance = ThemeMetrics(self)
        self.layout = ScaledLayout(self, self.appearance)
        self.content.columnconfigure(0, weight=1, uniform="hand_settings")
        self.content.columnconfigure(1, weight=1, uniform="hand_settings")
        self.model = LandmarkerModelSection(self.content, on_change=self.notify_change, asset=model_asset)
        self.add_section("Landmarker Model", self.model, row=0, column=0, padx=(0, 16), pady=(0, 16))
        self.tracking = TrackingSection(
            self.content, settings.data.theme,
            settings.data.max_finger_deviation,
            on_change=self.notify_change,
        )
        self.add_section("Tracking", self.tracking, row=1, column=0, padx=(0, 16))
        self.optimistic = OptimisticTrackingSection(
            self.content, on_change=self.notify_change, appearance=self.appearance,
        )
        self.add_section("Optimistic Tracking", self.optimistic, row=0, column=1, rowspan=2)

    @property
    def tracking_preview_active(self):
        return self.tracking.deviation.preview.visible

    def set_preview_data(self, fingers, status):
        self.tracking.deviation.preview.set_data(fingers, status)
