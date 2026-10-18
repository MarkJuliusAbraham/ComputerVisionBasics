"""Settings for the optional landmark coordinate filter."""

from tkinter import ttk

from hand_tracking.frontend.components.field_section import FieldSection, FieldSpec
from hand_tracking.frontend.components.text_wrap import WrapToWidth


class OneEuroSection(FieldSection):
    def __init__(self, master, on_change=None):
        super().__init__(master, "One Euro Filter", (
            FieldSpec("one_euro_enabled", "Filter landmark coordinates", "check"),
            FieldSpec("one_euro_min_cutoff_hz", "Minimum cutoff (Hz)", "number",
                      minimum=0.01, maximum=100, increment=0.1),
            FieldSpec("one_euro_beta", "Speed response (beta)", "number",
                      minimum=0, maximum=100, increment=0.1),
        ), on_change)
        self.cutoff_hint = ttk.Label(self.rows[1], text=(
            "0.1 Hz: strong smoothing, more lag. 1 Hz: starting point. "
            "10 Hz: lighter smoothing. 100 Hz: close to raw input. "
            "At 100 Hz, each update uses about 91–95% of the new measurement "
            "at 30–60 updates/sec, before speed adaptation. Zero is not valid."
        ), justify="left", width=1, wraplength=self.appearance.pixels(420))
        self.layout.grid(self.cutoff_hint, row=1, column=0, columnspan=2,
                         sticky="ew", pady=(4, 0))
        self.beta_hint = ttk.Label(self.rows[2], text=(
            "0: disables speed adaptation, not smoothing. 0.5: starting point. "
            "Higher values reduce smoothing as movement gets faster, trading "
            "steadiness for responsiveness. There is no universal beta value "
            "that turns filtering off; its effect depends on movement speed."
        ), justify="left", width=1, wraplength=self.appearance.pixels(420))
        self.layout.grid(self.beta_hint, row=1, column=0, columnspan=2,
                         sticky="ew", pady=(4, 0))
        self.hint = ttk.Label(self, text=(
            "Uncheck Filter landmark coordinates to turn this layer completely off. "
            "Applies before gesture recognition. "
            "Optimistic wrist smoothing remains a separate setting."
        ), justify="left", width=1, wraplength=self.appearance.pixels(420))
        self.layout.pack(self.hint, anchor="w", fill="x", pady=(8, 0))
        self.wrap = WrapToWidth(self, (self.cutoff_hint, self.beta_hint, self.hint), self.appearance)

    def load(self, data):
        self.load_values({field.key: getattr(data, field.key) for field in self.fields})
