"""Keep editable fields aligned with the active theme's typography."""

from gui_tkinter.core.widget_tree import walk_widgets


class ThemeTypography:
    FIELD_CLASSES = ("TEntry", "TCombobox", "TSpinbox")

    def __init__(self, root, font_name):
        self.root = root
        self.font_name = font_name

    def apply(self):
        for widget_class in self.FIELD_CLASSES:
            self.root.option_add(f"*{widget_class}.font", self.font_name)
        for widget in walk_widgets(self.root, include_parent=False):
            if widget.winfo_class() in self.FIELD_CLASSES:
                widget.configure(font=self.font_name)
