"""Hand-specific detection controls."""

from hand_tracking.backend.gestures.finger_classifier import FingerClassifier
from hand_tracking.frontend.components.field_section import FieldSection, FieldSpec
from hand_tracking.frontend.components.text_wrap import WrapToWidth
from tkinter import ttk

from .deviation_settings import DeviationSettings


class TrackingSection(FieldSection):
    def __init__(self, master, theme_name, max_deviation, on_change=None):
        super().__init__(master, "Hand tracking", (
            FieldSpec("track_hands", "Enable hand tracking", "check"),
            FieldSpec("finger_hysteresis_enabled", "Enable finger classification hysteresis", "check"),
            FieldSpec("finger_hysteresis_margin_degrees", "Hysteresis margin (degrees)", "number",
                      minimum=0, maximum=30, increment=0.5),
            FieldSpec("finger_deviation_calculation", "Deviation calculation", "choice",
                      options=FingerClassifier.CALCULATIONS),
        ), on_change)
        self.hint = ttk.Label(self, text=(
            "Each finger keeps its category until its bend crosses the boundary plus "
            "or minus this margin. Larger margins resist flicker but require more "
            "movement to switch. Zero disables hysteresis."
        ), width=1, wraplength=self.appearance.pixels(420), justify="left")
        self.layout.pack(self.hint, fill="x", pady=(4, 8))
        self.wrap = WrapToWidth(self, (self.hint,), self.appearance)
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
            "finger_hysteresis_enabled": data.finger_hysteresis_enabled,
            "finger_hysteresis_margin_degrees": data.finger_hysteresis_margin_degrees,
            "finger_deviation_calculation": data.finger_deviation_calculation,
        })
        self.deviation.load(data)

    def set_theme(self, theme_name):
        self.deviation.set_theme(theme_name)
