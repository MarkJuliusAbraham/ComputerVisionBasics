"""Keep editable fields aligned with the active theme's typography."""

class ThemeTypography:
    FIELD_CLASSES = ("TEntry", "TCombobox", "TSpinbox")

    def __init__(self, root, font_name):
        self.root = root
        self.font_name = font_name

    def apply(self):
        for widget_class in self.FIELD_CLASSES:
            self.root.option_add(f"*{widget_class}.font", self.font_name)
        self._update_fields(self.root)

    def _update_fields(self, parent):
        # Python-owned children exclude Tk's internal popup widgets, which
        # winfo_children() cannot always resolve back to Python instances.
        for widget in tuple(parent.children.values()):
            if widget.winfo_class() in self.FIELD_CLASSES:
                widget.configure(font=self.font_name)
            self._update_fields(widget)
