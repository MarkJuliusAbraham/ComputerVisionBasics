"""Folder controls, profile table, and a permanently reserved action footer."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.theme import ThemeMetrics
from ..display_names import profile_display_name
from .profile_table import ProfileTable


class ProfilePickerView(ttk.Frame):
    """Folder controls, profile table, and a permanently reserved action footer."""

    def __init__(self, master, on_browse, on_create, on_confirm, on_cancel):
        appearance = ThemeMetrics(master)
        scale = appearance.scale
        gap = round(12 * scale)
        padding = round(20 * scale)
        super().__init__(master, padding=padding)
        self.appearance = appearance
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        self.body_font = appearance.font
        self.strong_font = appearance.heading_font
        self.title_font = appearance.font_variant(size_delta=3, weight="bold")

        ttk.Label(self, text="Gesture profiles", font=self.title_font).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            self, text="Select a profile, then confirm to activate it."
        ).grid(row=1, column=0, sticky="w", pady=(round(4 * scale), gap))

        folder = ttk.Frame(self)
        folder.grid(row=2, column=0, sticky="ew", pady=(0, gap))
        folder.columnconfigure(0, weight=1)
        ttk.Label(folder, text="Profile folder", font=self.strong_font).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, gap // 2)
        )
        self.folder = tk.StringVar(self)
        ttk.Entry(folder, textvariable=self.folder, state="readonly", width=1).grid(
            row=1, column=0, sticky="ew", padx=(0, gap)
        )
        ttk.Button(folder, text="Browse…", command=on_browse, width=11).grid(
            row=1, column=1, sticky="e"
        )

        toolbar = ttk.Frame(self)
        toolbar.grid(row=3, column=0, sticky="ew", pady=(0, gap))
        toolbar.columnconfigure(2, weight=1)
        ttk.Label(toolbar, text="Available profiles", font=self.strong_font).grid(
            row=0, column=0, sticky="w"
        )
        self.profile_count = tk.StringVar(self)
        ttk.Label(toolbar, textvariable=self.profile_count).grid(
            row=0, column=1, sticky="w", padx=(gap, 0)
        )
        create_button = ttk.Button(toolbar, text="Create profile…", command=on_create)
        create_button.grid(row=0, column=3, sticky="e")
        if on_create is None:
            create_button.state(["disabled"])

        self.table = ProfileTable(
            self, self.appearance, self._selection_changed,
        )
        self.table.grid(row=4, column=0, sticky="nsew")
        ttk.Separator(self, orient="horizontal").grid(
            row=5, column=0, sticky="ew", pady=(gap, gap)
        )

        footer = ttk.Frame(self)
        footer.grid(row=6, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        selection = ttk.Frame(footer)
        selection.grid(row=0, column=0, sticky="ew", padx=(0, gap))
        selection.columnconfigure(0, weight=1)
        ttk.Label(selection, text="Selected profile").grid(row=0, column=0, sticky="w")
        self.selection_name = tk.StringVar(self, value="No profile selected")
        ttk.Label(selection, textvariable=self.selection_name,
                  font=self.strong_font, width=1, anchor="w").grid(
            row=1, column=0, sticky="ew", pady=(round(3 * scale), 0)
        )
        ttk.Button(footer, text="Cancel", command=on_cancel, width=11).grid(
            row=0, column=1, padx=(0, gap)
        )
        self.confirm_button = ttk.Button(
            footer, text="Confirm", command=on_confirm, width=11,
            style="Accent.TButton",
        )
        self.confirm_button.grid(row=0, column=2)
        self.confirm_button.state(["disabled"])

    def show_folder(self, folder, profiles, active_profile, selected_profile=None):
        self.folder.set(str(folder))
        self.profile_count.set(f"({len(profiles)})")
        self.table.show_profiles(profiles, active_profile, selected_profile)

    @property
    def selected_profile(self):
        return self.table.selected_profile

    def _selection_changed(self, profile):
        self.selection_name.set(profile_display_name(profile) if profile else "No profile selected")
        self.confirm_button.state(["!disabled"] if profile else ["disabled"])
