from dataclasses import replace
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import font as tkfont

from gui_tkinter.components.buttons import DiscardChangesButton

from ..display_names import gesture_display_names


class GestureManagerDialog:
    """Stage gesture creation, deletion, and renaming before saving the profile."""

    def __init__(self, master, gestures, on_create, on_save):
        self.master = master
        self._original = tuple(gestures)
        self._gestures = list(gestures)
        self.on_create = on_create
        self.on_save = on_save
        self._loading_name = False
        self._selected_id = None

    def show(self):
        self.window = tk.Toplevel(self.master)
        self.window.title("Manage Gestures")
        self.window.geometry("900x1200")
        self.window.resizable(False, False)
        self.window.transient(self.master)
        self.window.grab_set()

        content = ttk.Frame(self.window, padding=22)
        content.pack(fill="both", expand=True)
        ttk.Label(content, text="Manage Gestures",
                  font=("TkDefaultFont", 14, "bold")).pack(anchor="w")
        ttk.Label(
            content,
            text="Create gestures and edit their names. Save here to update the active profile.",
            wraplength=640,
        ).pack(anchor="w", pady=(6, 18))

        body = ttk.Frame(content)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1, uniform="manage")
        body.columnconfigure(1, weight=1, uniform="manage")
        body.rowconfigure(0, weight=1)

        list_group = ttk.LabelFrame(body, text="Available Gestures", padding=12)
        list_group.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        list_group.rowconfigure(0, weight=1)
        list_group.columnconfigure(0, weight=1)
        style = ttk.Style(self.window)
        tree_font_name = style.lookup("Treeview", "font") or "TkDefaultFont"
        try:
            tree_font = tkfont.nametofont(tree_font_name)
        except tk.TclError:
            tree_font = tkfont.Font(self.window, font=tree_font_name)
        style.configure(
            "GestureManager.Treeview",
            rowheight=tree_font.metrics("linespace") + 14,
        )
        self.gesture_list = ttk.Treeview(
            list_group, show="tree", selectmode="browse", height=8,
            style="GestureManager.Treeview",
        )
        self.gesture_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            list_group, orient="vertical", command=self.gesture_list.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.gesture_list.configure(yscrollcommand=scrollbar.set)
        self.gesture_list.bind("<<TreeviewSelect>>", self._selection_changed)

        list_actions = ttk.Frame(list_group)
        list_actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ttk.Button(list_actions, text="Create Gesture", command=self._create).pack(
            side="left"
        )
        self.delete_button = ttk.Button(
            list_actions, text="Delete Gesture", command=self._delete
        )
        self.delete_button.pack(side="right")

        details = ttk.LabelFrame(body, text="Gesture Details", padding=16)
        details.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        ttk.Label(details, text="Name").pack(anchor="w")
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(details, textvariable=self.name_var)
        self.name_entry.pack(fill="x", pady=(6, 0))
        self.name_var.trace_add("write", self._name_changed)
        ttk.Label(
            details,
            text="Names appear in the gesture selector. Criteria and commands are edited on the mapping page.",
            wraplength=255,
        ).pack(anchor="w", pady=(14, 0))

        footer = ttk.Frame(content)
        footer.pack(fill="x", pady=(18, 0))
        self.save_button = ttk.Button(
            footer, text="Save Gestures", command=self._save,
            style="Accent.TButton",
        )
        self.save_button.pack(side="right")
        DiscardChangesButton(footer, text="Discard", command=self._discard).pack(
            side="right", padx=(0, 8)
        )

        self._refresh_list()
        self._center_over_master()
        self.window.protocol("WM_DELETE_WINDOW", self._request_close)
        self.window.wait_window()

    def _center_over_master(self):
        self.window.update_idletasks()
        self.master.update_idletasks()
        width, height = 900, 1200
        left = self.master.winfo_rootx() + (self.master.winfo_width() - width) // 2
        top = self.master.winfo_rooty() + (self.master.winfo_height() - height) // 2
        max_left = max(0, self.window.winfo_screenwidth() - width)
        max_top = max(0, self.window.winfo_screenheight() - height)
        left = min(max(left, 0), max_left)
        top = min(max(top, 0), max_top)
        self.window.geometry(f"{width}x{height}+{left}+{top}")

    def _is_dirty(self):
        return tuple(self._gestures) != self._original

    def _refresh_save_state(self):
        self.save_button.state(["!disabled"] if self._is_dirty() else ["disabled"])

    def _refresh_list(self, select_id=None):
        self.gesture_list.delete(*self.gesture_list.get_children())
        for gesture, display_name in self._display_names():
            self.gesture_list.insert(
                "", "end", iid=gesture.id,
                text=display_name,
            )
        ids = {gesture.id for gesture in self._gestures}
        if select_id not in ids:
            select_id = self._gestures[0].id if self._gestures else None
        self._selected_id = select_id
        if select_id is not None:
            self.gesture_list.selection_set(select_id)
            self.gesture_list.focus(select_id)
            gesture = next(item for item in self._gestures if item.id == select_id)
            self._set_name(gesture.name)
        else:
            self._set_name("")
        self.delete_button.state(["!disabled"] if len(ids) > 1 else ["disabled"])
        self.name_entry.state(["!disabled"] if ids else ["disabled"])
        self._refresh_save_state()

    def _set_name(self, value):
        self._loading_name = True
        self.name_var.set(value)
        self._loading_name = False

    def _selection_changed(self, _event=None):
        selection = self.gesture_list.selection()
        if not selection or selection[0] == self._selected_id:
            return
        self._selected_id = selection[0]
        gesture = next(item for item in self._gestures if item.id == self._selected_id)
        self._set_name(gesture.name)

    def _name_changed(self, *_args):
        if self._loading_name or self._selected_id is None:
            return
        name = self.name_var.get().strip()
        self._gestures = [
            replace(gesture, name=name) if gesture.id == self._selected_id else gesture
            for gesture in self._gestures
        ]
        for gesture, display_name in self._display_names():
            self.gesture_list.item(gesture.id, text=display_name)
        self._refresh_save_state()

    def _display_names(self):
        return gesture_display_names(self._gestures)

    def _create(self):
        try:
            gesture = self.on_create(tuple(self._gestures))
        except ValueError as error:
            messagebox.showerror("Cannot Create Gesture", str(error), parent=self.window)
            return
        if gesture is not None:
            self._gestures.append(gesture)
            self._refresh_list(gesture.id)
            self.name_entry.focus_set()
            self.name_entry.selection_range(0, "end")

    def _delete(self):
        if self._selected_id is None:
            return
        if not messagebox.askyesno(
            "Delete Gesture",
            "Delete this gesture from the active profile?",
            parent=self.window,
        ):
            return
        self._gestures = [
            gesture for gesture in self._gestures if gesture.id != self._selected_id
        ]
        self._refresh_list()

    def _save(self):
        try:
            self.on_save(tuple(self._gestures), self._selected_id)
        except (OSError, ValueError) as error:
            messagebox.showerror("Could Not Save Gestures", str(error), parent=self.window)
            return
        self.window.destroy()

    def _discard(self):
        self.window.destroy()

    def _request_close(self):
        if not self._is_dirty():
            self.window.destroy()
            return
        from gui_tkinter.components.unapplied_changes_dialog import UnappliedChangesDialog

        choice = UnappliedChangesDialog(
            self.window, context="Gesture Manager", action_label="Save"
        ).show()
        if choice == "save":
            self._save()
        elif choice == "discard":
            self._discard()

