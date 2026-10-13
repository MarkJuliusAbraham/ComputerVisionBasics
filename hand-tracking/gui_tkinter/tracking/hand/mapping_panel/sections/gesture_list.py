"""Fixed-width gesture browser and related management actions."""

from gui_tkinter.core.idle_refresh import IdleRefresh
from tkinter import ttk

from ..display_names import gesture_display_names
from .gesture_context_menu import GestureContextMenu


class GestureListSection(ttk.Frame):
    def __init__(
        self, master, appearance, *, on_select=None, on_manage=None, on_reset=None,
        on_rename=None, on_delete=None,
    ):
        super().__init__(master)
        self.appearance = appearance
        self._on_select = on_select
        self._selected_id = None
        self._names = {}
        self._invalid_ids = frozenset()
        self._style_name = f"GestureBrowser{id(self)}.Treeview"
        self._invalid_style_name = f"Invalid.{self._style_name}"
        self._style_snapshot = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.grid_propagate(False)
        ttk.Label(self, text="Gestures", font=appearance.heading_font).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, appearance.pixels(10)),
        )
        self.list = ttk.Treeview(
            self, show="tree", selectmode="browse", height=8,
            style=self._style_name,
        )
        self.list.column("#0", width=appearance.pixels(160), minwidth=0, stretch=True)
        self.list.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.list.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.list.configure(yscrollcommand=scrollbar.set)
        self.list.bind("<<TreeviewSelect>>", self._selection_changed)
        self.context_menu = None
        if on_rename or on_delete:
            self.context_menu = GestureContextMenu(
                self.list, on_select=self.select, on_rename=on_rename, on_delete=on_delete,
                can_delete=lambda _gesture_id: len(self._names) > 1, font=appearance.font,
            )
        ttk.Button(self, text="Manage gestures", command=on_manage).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(appearance.pixels(12), 0),
        )
        ttk.Separator(self).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=appearance.pixels(18),
        )
        ttk.Label(self, text="Profile behavior", font=appearance.heading_font).grid(
            row=4, column=0, columnspan=2, sticky="w",
        )
        ttk.Button(self, text="Edit universal reset", command=on_reset).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(appearance.pixels(8), 0),
        )
        self._refresh_layout()
        self.theme_refresh = IdleRefresh(self, self._refresh_layout, event="<<ThemeChanged>>")

    def _refresh_layout(self):
        self.appearance.refresh()
        self.configure(width=self.appearance.pixels(210))
        style = ttk.Style(self)
        height = self.appearance.font.metrics("linespace") + self.appearance.pixels(16)
        alert = self.appearance.colors.high_alert
        snapshot = (style.theme_use(), height, alert)
        # Style changes can publish ThemeChanged; store the snapshot first so
        # a resulting refresh cannot repeatedly reconfigure the same style.
        if snapshot != self._style_snapshot:
            self._style_snapshot = snapshot
            self.list.tag_configure("invalid", foreground=alert.foreground)
            style.configure(self._style_name, rowheight=height)
            style.map(
                self._style_name, foreground=style.map("Treeview", "foreground"),
                background=style.map("Treeview", "background"),
            )
            # A selected-state map normally overrides item tag colors. Keep
            # the warning readable when this invalid gesture is selected too.
            style.map(
                self._invalid_style_name, foreground=[("selected", alert.foreground)],
                background=[("selected", alert.selection_background)],
            )
        selected_style = (
            self._invalid_style_name if self._selected_id in self._invalid_ids else self._style_name
        )
        if self.list.cget("style") != selected_style:
            # Selection switches prebuilt styles without publishing global
            # style changes and repainting every other form component.
            self.list.configure(style=selected_style)

    def load(self, definitions, selected_id):
        self._selected_id = selected_id
        self._names = {
            definition.id: label for definition, label in gesture_display_names(definitions)
        }
        items = self.list.get_children()
        if items:
            self.list.delete(*items)
        for gesture_id, label in self._names.items():
            self.list.insert(
                "", "end", iid=gesture_id, text=label,
                tags=("invalid",) if gesture_id in self._invalid_ids else (),
            )
        if selected_id in self._names:
            self.list.selection_set(selected_id)
            self.list.focus(selected_id)
            self.list.see(selected_id)
        self._refresh_layout()

    @property
    def display_names(self):
        return self._names.copy()

    def show_validation(self, invalid_ids):
        invalid_ids = frozenset(invalid_ids)
        if invalid_ids != self._invalid_ids:
            self._invalid_ids = invalid_ids
            for gesture_id in self.list.get_children():
                self.list.item(gesture_id, tags=("invalid",) if gesture_id in invalid_ids else ())
            self._refresh_layout()

    def display_name(self, gesture_id):
        return self._names.get(gesture_id)

    def _selection_changed(self, _event):
        selected = self.list.selection()
        if selected:
            self._notify_selection(selected[0])

    def select(self, gesture_id):
        self.list.selection_set(gesture_id)
        self.list.focus(gesture_id)
        self.list.see(gesture_id)
        self._notify_selection(gesture_id)

    def _notify_selection(self, gesture_id):
        if gesture_id == self._selected_id:
            return
        self._selected_id = gesture_id
        self._refresh_layout()
        if self._on_select:
            self._on_select(self._selected_id)
