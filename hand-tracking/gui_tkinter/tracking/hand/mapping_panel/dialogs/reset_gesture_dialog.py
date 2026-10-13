"""Stage profile-wide reset criteria without saving the profile implicitly."""

from tkinter import ttk

from gui_tkinter.components.scrollable_frame import ScrollableFrame
from gui_tkinter.components.theme import ThemeMetrics
from gui_tkinter.core.modal_dialog import ModalDialog

from ..sections.reset_gesture import ResetGestureSection


class ResetGestureDialog:
    def __init__(self, parent, match, segment_count, on_use_changes):
        self.parent = parent
        self.match = match
        self.segment_count = segment_count
        self.on_use_changes = on_use_changes

    def show(self):
        self.modal = ModalDialog(self.parent, "Edit universal reset", base_size=(900, 700))
        self.window = self.modal.window
        appearance = ThemeMetrics(self.window)
        footer = ttk.Frame(self.window, padding=appearance.pixels(16))
        footer.pack(side="bottom", fill="x")
        ttk.Button(footer, text="Use changes", command=self._use_changes,
                   style="Accent.TButton").pack(side="right")
        ttk.Button(footer, text="Cancel", command=self.window.destroy).pack(
            side="right", padx=(0, appearance.pixels(8)),
        )
        ttk.Label(footer, text="Commit these changes with Save mappings.").pack(
            side="left", padx=(0, appearance.pixels(12)),
        )
        scroll = ScrollableFrame(self.window)
        scroll.pack(fill="both", expand=True, padx=appearance.pixels(16), pady=(appearance.pixels(16), 0))
        self.section = ResetGestureSection(scroll.content, segment_count=self.segment_count)
        self.section.pack(fill="x")
        self.section.load(self.match)
        self.modal.show(scale=appearance.scale)

    def _use_changes(self):
        self.on_use_changes(self.section.values())
        self.window.destroy()
