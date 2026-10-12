"""Stage profile-wide reset criteria without saving the profile implicitly."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.scrollable_frame import ScrollableFrame
from gui_tkinter.components.theme import ThemeMetrics
from gui_tkinter.core.window_geometry import WindowGeometry

from ..sections.reset_gesture import ResetGestureSection


class ResetGestureDialog:
    def __init__(self, parent, match, segment_count, on_use_changes):
        self.parent = parent
        self.match = match
        self.segment_count = segment_count
        self.on_use_changes = on_use_changes

    def show(self):
        self.window = tk.Toplevel(self.parent)
        self.window.withdraw()
        self.window.title("Edit universal reset")
        self.window.transient(self.parent)
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
        geometry = WindowGeometry(self.window, (900, 700))
        geometry.resize(appearance.scale)
        geometry.place_near(self.parent)
        self.window.bind("<Escape>", lambda _event: self.window.destroy())
        self.window.deiconify()
        self.window.wait_visibility()
        self.window.grab_set()
        self.window.focus_set()
        self.window.wait_window()

    def _use_changes(self):
        self.on_use_changes(self.section.values())
        self.window.destroy()
