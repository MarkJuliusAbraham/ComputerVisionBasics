"""Selectable profile table, separate from folder controls and dialog actions."""

from collections import Counter
from pathlib import Path
from tkinter import ttk

from hand_tracking.ui.core.idle_refresh import IdleRefresh
from ..display_names import profile_display_name


class ProfileTable(ttk.Frame):
    """Selectable profile rows with static, aligned column labels."""

    def __init__(self, master, appearance, on_select):
        super().__init__(master)
        self._on_select = on_select
        body_font, heading_font, pixels = appearance.font, appearance.heading_font, appearance.pixels
        self._profiles_by_id = {}
        self._header_padding = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        status_width = max(
            pixels(90), heading_font.measure("Status") + pixels(24)
        )

        header = self.header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, pixels(7)))
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, minsize=status_width)
        for column, text in enumerate(("Profile", "Status")):
            ttk.Label(header, text=text, font=heading_font).grid(
                row=0, column=column, sticky="w", padx=(pixels(4), 0)
            )
        ttk.Separator(self, orient="horizontal").grid(
            row=1, column=0, sticky="ew"
        )

        ttk.Style(self).configure(
            "ProfilePicker.Treeview", font=body_font,
            rowheight=max(body_font.metrics("linespace") + pixels(16),
                          pixels(34)),
        )
        self.tree = ttk.Treeview(
            self, columns=("profile", "status"), show="", height=6,
            selectmode="browse", style="ProfilePicker.Treeview",
        )
        self.tree.column("profile", width=pixels(400),
                         minwidth=pixels(100), stretch=True, anchor="w")
        self.tree.column("status", width=status_width, minwidth=status_width,
                         stretch=False, anchor="w")
        self.tree.grid(row=2, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(self, command=self.tree.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)
        self.header_refresh = IdleRefresh(self, self._align_header)
        self.tree.bind("<Configure>", self.header_refresh.schedule)

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
        names = Counter(profile_display_name(profile) for profile in profiles)
        for index, profile in enumerate(profiles):
            profile = Path(profile)
            item = str(index)
            self._profiles_by_id[item] = profile
            name = profile_display_name(profile)
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
        self.header_refresh.schedule()
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


