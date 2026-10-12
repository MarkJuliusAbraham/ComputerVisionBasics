"""Mapping panel entry point for the restored Tkinter UI."""
from .mapping_editor import MappingEditor


class MappingPanel:
    """Deferred mapping editor that can be attached to a control window.

    The panel is created before the window so the application can own this
    component, while the actual Tk widget is built after ``ControlWindow`` has
    created its notebook parent.
    """

    def __init__(self, on_saved=None, config_path=None, segment_count=4):
        self.on_saved = on_saved
        self.config_path = config_path
        self.segment_count = segment_count
        self.widget = None

    def build(self, parent):
        self.widget = MappingEditor(
            parent, on_saved=self.on_saved, config_path=self.config_path,
            segment_count=self.segment_count,
        )
        self.widget.pack(fill="both", expand=True)
        return self.widget

    def set_segment_count(self, segment_count):
        self.segment_count = segment_count
        if self.widget is not None:
            self.widget.set_segment_count(segment_count)

