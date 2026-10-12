"""Active profile display and access to profile selection."""

from pathlib import Path
import tkinter as tk
from tkinter import ttk


class ProfileSection(ttk.Frame):
    """Show the active profile name without exposing its storage path."""

    def __init__(self, master, on_choose=None):
        super().__init__(master)
        details = ttk.Frame(self)
        details.pack(side="left", fill="x", expand=True, padx=(0, 18))
        ttk.Label(details, text="ACTIVE PROFILE", font=("TkDefaultFont", 8, "bold")).pack(anchor="w")
        self.name = tk.StringVar(self)
        ttk.Label(details, textvariable=self.name, font=("TkDefaultFont", 15, "bold")).pack(
            anchor="w", pady=(2, 1)
        )
        ttk.Button(self, text="More Profiles", command=on_choose).pack(side="right", anchor="center")

    def load(self, path):
        profile = Path(path)
        name = profile.stem.replace("_", " ").replace("-", " ").title()
        self.name.set(name or profile.name)
