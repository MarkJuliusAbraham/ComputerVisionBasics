"""Hand-specific detection controls."""

from hand_tracking.gestures.finger_classifier import FingerClassifier
from hand_tracking.ui.components.field_section import FieldSection, FieldSpec

from .deviation_settings import DeviationSettings


class TrackingSection(FieldSection):
    def __init__(self, master, theme_name, max_deviation, on_change=None):
        super().__init__(master, "Hand tracking", (
            FieldSpec("track_hands", "Enable hand tracking", "check"),
            FieldSpec("finger_deviation_calculation", "Deviation calculation", "choice",
                      options=FingerClassifier.CALCULATIONS),
        ), on_change)
        self.deviation = DeviationSettings(
            self, theme_name, max_deviation, on_change=self.changes.emit,
        )
        self.deviation.pack(fill="x")
        self.variables.update(self.deviation.variables)

    def values(self):
        return {**super().values(), **self.deviation.values()}

    def draft_values(self):
        return {**super().draft_values(), **self.deviation.values()}

    def load(self, data):
        self.load_values({
            "track_hands": data.track_hands,
            "finger_deviation_calculation": data.finger_deviation_calculation,
        })
        self.deviation.load(data)

    def set_theme(self, theme_name):
        self.deviation.set_theme(theme_name)
