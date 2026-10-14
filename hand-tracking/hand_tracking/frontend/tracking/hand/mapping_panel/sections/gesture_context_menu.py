"""Context actions for the quick-access gesture browser."""

import tkinter as tk


class GestureContextMenu:
    def __init__(self, tree, *, on_select, on_rename, on_delete, can_delete, font):
        self.tree = tree
        self._on_select = on_select
        self._on_rename = on_rename
        self._on_delete = on_delete
        self._can_delete = can_delete
        self._gesture_id = None
        self.menu = tk.Menu(tree, tearoff=False, font=font)
        self.menu.add_command(label="Rename…", command=lambda: self._invoke(self._on_rename))
        self.menu.add_command(label="Delete", command=lambda: self._invoke(self._on_delete))
        tree.bind("<Button-3>", self._show, add="+")

    def _show(self, event):
        gesture_id = self.tree.identify_row(event.y)
        if not gesture_id:
            return "break"
        self._gesture_id = gesture_id
        # Selecting synchronously captures the previous gesture's draft before
        # a popup action can edit the newly selected gesture.
        self._on_select(gesture_id)
        self.menu.entryconfigure(0, state="normal" if self._on_rename else "disabled")
        self.menu.entryconfigure(
            1, state="normal" if self._on_delete and self._can_delete(gesture_id) else "disabled",
        )
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()
        return "break"

    def _invoke(self, action):
        if action and self._gesture_id and self.tree.exists(self._gesture_id):
            self.menu.unpost()
            self.menu.grab_release()
            action(self._gesture_id)
