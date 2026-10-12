"""Hand-specific detection controls."""

from gui_tkinter.settings_panel.sections import FieldSection, FieldSpec

from .deviation_settings import DeviationSettings


class TrackingSection(FieldSection):
    def __init__(self, master, theme_name, max_deviation, on_change=None):
        super().__init__(master, "Hand tracking", (
            FieldSpec("track_hands", "Enable hand tracking", "check"),
            FieldSpec("finger_deviation_calculation", "Deviation calculation", "choice",
                      options=("default", "prototype")),
        ), on_change)
        self.deviation = DeviationSettings(
            self, theme_name, max_deviation, on_change=self._notify_change,
        )
        self.deviation.pack(fill="x")
        self.variables.update(self.deviation.variables)

    def values(self):
        return {**super().values(), **self.deviation.values()}

    def load(self, data):
        self.load_values({
            "track_hands": data.track_hands,
            "finger_deviation_calculation": data.finger_deviation_calculation,
        })
        self.deviation.load(data)

    def set_theme(self, theme_name):
        self.deviation.set_theme(theme_name)
