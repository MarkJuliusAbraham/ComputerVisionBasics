"""Gesture manager widgets; membership and persistence belong to its controller."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.commit_actions import CommitActions
from gui_tkinter.core.change_notifications import ChangeNotifications
from gui_tkinter.core.idle_refresh import IdleRefresh

from ..display_names import gesture_display_names


class GestureManagerView(ttk.Frame):
    def __init__(
        self, master, appearance, *, on_select, on_rename, on_create, on_delete,
        on_save, on_discard,
    ):
        super().__init__(master, padding=appearance.pixels(22))
        self.appearance = appearance
        self.changes = ChangeNotifications(self, on_rename)
        self.actions = CommitActions(
            self, on_save=on_save, on_discard=on_discard,
            save_label="Save Gestures", discard_label="Discard", appearance=appearance,
        )
        self.actions.pack(side="bottom", fill="x", pady=(appearance.pixels(18), 0))
        self.title_font = appearance.font_variant(size_delta=5, weight="bold")
        ttk.Label(self, text="Manage Gestures", font=self.title_font).pack(anchor="w")
        ttk.Label(
            self, text="Create gestures and edit their names. Save here to update the active profile.",
            wraplength=appearance.pixels(640),
        ).pack(anchor="w", pady=(appearance.pixels(6), appearance.pixels(18)))
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        for column in (0, 1):
            body.columnconfigure(column, weight=1, uniform="manage")
        body.rowconfigure(0, weight=1)
        list_group = ttk.LabelFrame(body, text="Available Gestures", padding=appearance.pixels(12))
        list_group.grid(row=0, column=0, sticky="nsew", padx=(0, appearance.pixels(10)))
        list_group.rowconfigure(0, weight=1)
        list_group.columnconfigure(0, weight=1)
        self.style_name = f"GestureManager{id(self)}.Treeview"
        self.list = ttk.Treeview(
            list_group, show="tree", selectmode="browse", height=8, style=self.style_name,
        )
        self.list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_group, orient="vertical", command=self.list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(appearance.pixels(8), 0))
        self.list.configure(yscrollcommand=scrollbar.set)
        self.list.bind("<<TreeviewSelect>>", lambda _event: on_select(self.selected_id))
        list_actions = ttk.Frame(list_group)
        list_actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(appearance.pixels(14), 0))
        ttk.Button(list_actions, text="Create Gesture", command=on_create).pack(side="left")
        self.delete_button = ttk.Button(list_actions, text="Delete Gesture", command=on_delete)
        self.delete_button.pack(side="right")
        details = ttk.LabelFrame(body, text="Gesture Details", padding=appearance.pixels(16))
        details.grid(row=0, column=1, sticky="nsew", padx=(appearance.pixels(10), 0))
        ttk.Label(details, text="Name").pack(anchor="w")
        self.name = tk.StringVar(self)
        self.entry = ttk.Entry(details, textvariable=self.name)
        self.entry.pack(fill="x", pady=(appearance.pixels(6), 0))
        self.changes.watch(self.name)
        ttk.Label(
            details, text="Names appear in the gesture selector. Criteria and commands are edited on the mapping page.",
            wraplength=appearance.pixels(255),
        ).pack(anchor="w", pady=(appearance.pixels(14), 0))
        self._style_snapshot = None
        self.theme_refresh = IdleRefresh(self, self._refresh_style, event="<<ThemeChanged>>")
        self._refresh_style()

    def _refresh_style(self):
        self.appearance.refresh()
        style = ttk.Style(self)
        height = self.appearance.font.metrics("linespace") + self.appearance.pixels(14)
        snapshot = (style.theme_use(), height)
        if snapshot != self._style_snapshot:
            self._style_snapshot = snapshot
            style.configure(self.style_name, rowheight=height)

    @property
    def selected_id(self):
        selection = self.list.selection()
        return selection[0] if selection else None

    def show_collection(self, draft):
        items = self.list.get_children()
        if items:
            self.list.delete(*items)
        for definition, label in gesture_display_names(draft.definitions):
            self.list.insert("", "end", iid=definition.id, text=label)
        if draft.selected is not None:
            self.list.selection_set(draft.selected_id)
            self.list.focus(draft.selected_id)
            self.list.see(draft.selected_id)
        self.show_name(draft.selected.name if draft.selected is not None else "")
        self.delete_button.state(["!disabled"] if len(draft.definitions) > 1 else ["disabled"])
        self.entry.state(["!disabled"] if draft.definitions else ["disabled"])
        self.actions.set_dirty(draft.is_dirty)

    def show_name(self, name):
        with self.changes.suspended():
            self.name.set(name)

    def refresh_names(self, draft):
        for definition, label in gesture_display_names(draft.definitions):
            self.list.item(definition.id, text=label)
        self.actions.set_dirty(draft.is_dirty)
