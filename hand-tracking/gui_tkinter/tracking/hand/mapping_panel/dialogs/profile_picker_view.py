"""Themed profile table and selection form for the profile picker."""

from collections import Counter
from pathlib import Path
import tkinter as tk
from tkinter import font as tkfont, ttk


def _profile_name(path):
    path = Path(path)
    return path.stem.replace("_", " ").replace("-", " ").title() or path.name


class ProfileTable(ttk.Frame):
    """Selectable profile rows with static, aligned column labels."""

    def __init__(self, master, body_font, heading_font, scale, on_select):
        super().__init__(master)
        self._on_select = on_select
        self._profiles_by_id = {}
        self._header_padding = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        status_width = max(
            int(90 * scale), heading_font.measure("Status") + int(24 * scale)
        )

        header = self.header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, int(7 * scale)))
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, minsize=status_width)
        for column, text in enumerate(("Profile", "Status")):
            ttk.Label(header, text=text, font=heading_font).grid(
                row=0, column=column, sticky="w", padx=(int(4 * scale), 0)
            )
        ttk.Separator(self, orient="horizontal").grid(
            row=1, column=0, sticky="ew"
        )

        ttk.Style(self).configure(
            "ProfilePicker.Treeview", font=body_font,
            rowheight=max(body_font.metrics("linespace") + int(16 * scale),
                          int(34 * scale)),
        )
        self.tree = ttk.Treeview(
            self, columns=("profile", "status"), show="", height=6,
            selectmode="browse", style="ProfilePicker.Treeview",
        )
        self.tree.column("profile", width=int(400 * scale),
                         minwidth=int(100 * scale), stretch=True, anchor="w")
        self.tree.column("status", width=status_width, minwidth=status_width,
                         stretch=False, anchor="w")
        self.tree.grid(row=2, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(self, command=self.tree.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)
        self.tree.bind("<Configure>", lambda _event: self.after_idle(self._align_header))

        self.empty_message = ttk.Label(
            self, text="No profiles found.\nBrowse another folder or create a profile.",
            justify="center", anchor="center",
        )

    def show_profiles(self, profiles, active_profile, selected_profile=None):
        self.tree.delete(*self.tree.get_children())
        self._profiles_by_id = {}
        active = Path(active_profile).resolve() if active_profile else None
        selected = selected_profile if selected_profile is not None else active
        selected = Path(selected).resolve() if selected is not None else None
        names = Counter(_profile_name(profile) for profile in profiles)
        for index, profile in enumerate(profiles):
            profile = Path(profile)
            item = str(index)
            self._profiles_by_id[item] = profile
            name = _profile_name(profile)
            if names[name] > 1:
                name = f"{name} · {profile.name}"
            self.tree.insert(
                "", "end", iid=item,
                values=(name, "Active" if profile.resolve() == active else ""),
            )
            if profile.resolve() == selected:
                self.tree.selection_set(item)
                self.tree.focus(item)
                self.tree.see(item)
        if profiles:
            self.empty_message.place_forget()
        else:
            self.empty_message.place(in_=self.tree, relx=0.5, rely=0.5, anchor="center")
        self.after_idle(self._align_header)
        self._selection_changed()

    def _align_header(self):
        # Native themes add their own inset around Treeview cells. Use the
        # displayed cell bounds so the label row follows that inset exactly.
        for item in self.tree.get_children():
            bounds = self.tree.bbox(item)
            if bounds:
                left, _top, width, _height = bounds
                padding = (left, 0, max(0, self.tree.winfo_width() - left - width), 0)
                if padding != self._header_padding:
                    self._header_padding = padding
                    self.header.configure(padding=padding)
                break

    @property
    def selected_profile(self):
        selection = self.tree.selection()
        return self._profiles_by_id.get(selection[0]) if selection else None

    def _selection_changed(self, _event=None):
        self._on_select(self.selected_profile)


class ProfilePickerView(ttk.Frame):
    """Folder controls, profile table, and a permanently reserved action footer."""

    def __init__(self, master, on_browse, on_create, on_confirm, on_cancel):
        scale = float(master.tk.call("tk", "scaling")) * 72 / 96
        gap = round(12 * scale)
        padding = round(20 * scale)
        super().__init__(master, padding=padding)
        self.scale = scale
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        theme_font = ttk.Style(self).lookup("TLabel", "font") or "TkDefaultFont"
        self.body_font = tkfont.Font(root=self, font=theme_font)
        self.strong_font = self.body_font.copy()
        self.strong_font.configure(weight="bold")
        self.title_font = self.strong_font.copy()
        self.title_font.configure(size=self.body_font.cget("size") + 3)

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
            self, self.body_font, self.strong_font, self.scale, self._selection_changed,
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

    @property
    def preferred_size(self):
        return round(720 * self.scale), round(560 * self.scale)

    def _selection_changed(self, profile):
        self.selection_name.set(_profile_name(profile) if profile else "No profile selected")
        self.confirm_button.state(["!disabled"] if profile else ["disabled"])
