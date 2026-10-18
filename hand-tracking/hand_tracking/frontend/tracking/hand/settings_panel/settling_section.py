"""Controls for motion-aware initial gesture activation."""

from tkinter import ttk

from hand_tracking.frontend.components.field_section import FieldSection, FieldSpec
from hand_tracking.frontend.components.text_wrap import WrapToWidth


class SettlingSection(FieldSection):
    def __init__(self, master, on_change=None):
        super().__init__(master, "Finger settling", (
            FieldSpec("finger_settling_enabled", "Wait for fingers to settle before activation", "check"),
            FieldSpec("finger_settling_max_speed", "Maximum bend speed (degrees/sec)", "number",
                      minimum=0, maximum=10000, increment=10),
        ), on_change)
        self.hint = ttk.Label(self, text=(
            "A matching gesture stays a candidate while relevant fingers are bending quickly. "
            "The latest match activates when their bend speed falls below this limit. "
            "Wrist movement does not count. No fixed hold timer is added. "
            "90 degrees/sec is a starting point (3 degrees per update at 30 updates/sec). "
            "Lower values reject more motion but can wait on jitter; higher values activate "
            "sooner but can admit intermediate poses. Zero requires identical bend angles. "
            "Uncheck to bypass. A newly seen hand needs two fresh results to estimate speed. "
            "Reset and active repeats keep their existing behavior."
        ), width=1, wraplength=self.appearance.pixels(420), justify="left")
        self.layout.pack(self.hint, fill="x", pady=(8, 0))
        self.wrap = WrapToWidth(self, (self.hint,), self.appearance)

    def load(self, data):
        self.load_values({field.key: getattr(data, field.key) for field in self.fields})
