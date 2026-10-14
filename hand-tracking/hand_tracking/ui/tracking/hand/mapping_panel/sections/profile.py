"""Active profile display and access to profile selection."""

import tkinter as tk
from tkinter import ttk
from hand_tracking.ui.components.theme import ThemeMetrics
from hand_tracking.ui.core.idle_refresh import IdleRefresh

from ..display_names import profile_display_name


class ProfileSection(ttk.Frame):
    """Show the active profile name without exposing its storage path."""

    def __init__(self, master, on_choose=None):
        super().__init__(master)
        self.appearance = ThemeMetrics(self)
        self.caption_font = self.appearance.font_variant(size_delta=-1, weight="bold")
        self.title_font = self.appearance.font_variant(size_delta=6, weight="bold")
        ttk.Button(self, text="More Profiles", command=on_choose).pack(side="right", anchor="center")
        details = ttk.Frame(self)
        details.pack(side="left", fill="x", expand=True, padx=(0, 18))
        ttk.Label(details, text="ACTIVE PROFILE", font=self.caption_font).pack(anchor="w")
        self.name = tk.StringVar(self)
        ttk.Label(details, textvariable=self.name, font=self.title_font, width=1).pack(
            fill="x", pady=(2, 1)
        )
        self.theme_refresh = IdleRefresh(self, self.appearance.refresh, event="<<ThemeChanged>>")

    def load(self, path):
        self.name.set(profile_display_name(path))
