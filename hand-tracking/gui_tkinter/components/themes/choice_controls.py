"""Scale native checkbox and radio indicators alongside theme typography."""


class ChoiceControlTheme:
    BASE_INDICATOR_SIZE = 14
    BASE_INDICATOR_MARGIN = (1, 1, 4, 1)
    BASE_PADDING = 2

    def __init__(self, palette):
        self.palette = palette

    def indicator_geometry(self, scale):
        return (
            self._pixels(self.BASE_INDICATOR_SIZE, scale),
            tuple(self._pixels(value, scale) for value in self.BASE_INDICATOR_MARGIN),
        )

    @staticmethod
    def _pixels(value, scale):
        return max(1, round(value * scale))

    def settings(self, scale):
        p = self.palette
        size, margins = self.indicator_geometry(scale)

        styles = {}
        for name in ("TCheckbutton", "TRadiobutton"):
            styles[name] = {
                "configure": {
                    "background": p.surface, "foreground": p.foreground,
                    # Clam's integer pixel dimensions do not follow tk scaling.
                    # Scale them explicitly, once, using the application's scale.
                    "indicatorsize": size,
                    "indicatormargin": margins,
                    "padding": self._pixels(self.BASE_PADDING, scale),
                    "indicatorbackground": p.field, "indicatorforeground": p.foreground,
                    "upperbordercolor": p.button_edges.shadow,
                    "lowerbordercolor": p.button_edges.highlight,
                },
                "map": {
                    "background": [("active", p.surface)],
                    "indicatorbackground": [
                        ("disabled", p.surface), ("alternate", p.hover), ("pressed", p.hover),
                    ],
                    "indicatorforeground": [("disabled", p.disabled)],
                    "upperbordercolor": [("disabled", p.border)],
                    "lowerbordercolor": [("disabled", p.border)],
                },
            }
        return styles
