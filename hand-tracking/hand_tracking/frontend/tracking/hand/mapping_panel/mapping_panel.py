"""Gesture mapping panel owned by the hand tracking workspace."""
import tkinter as tk
from .mapping_editor import MappingEditor


class MappingPanel:
    """Deferred mapping editor that can be attached to the hand window.

    The panel is created before the window so the application can own this
    component before its tracking window creates the notebook parent.
    """

    def __init__(self, on_saved=None, config_path=None, segment_count=4, *, pose_feed=None):
        self.on_saved = on_saved
        self.config_path = config_path
        self.segment_count = segment_count
        self.pose_feed = pose_feed
        self.widget: MappingEditor | None = None

    def build(self, parent: tk.Misc) -> MappingEditor:
        self.widget = MappingEditor(
            parent, on_saved=self.on_saved, config_path=self.config_path,
            segment_count=self.segment_count, pose_feed=self.pose_feed,
        )
        self.widget.pack(fill="both", expand=True)
        return self.widget

    def set_segment_count(self, segment_count):
        self.segment_count = segment_count
        if self.widget is not None:
            self.widget.set_segment_count(segment_count)

    def is_dirty(self) -> bool:
        return self.widget is not None and self.widget.is_dirty()

    def save(self) -> bool:
        return self.widget is None or self.widget.save()

    def discard(self) -> None:
        if self.widget is not None:
            self.widget.discard()

