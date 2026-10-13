"""Coordinate staged gesture membership and names with the manager view."""

from tkinter import messagebox

from gui_tkinter.components.theme import ThemeMetrics
from gui_tkinter.core.modal_dialog import ModalDialog
from gui_tkinter.core.unsaved_changes_guard import PendingChanges, UnsavedChangesGuard

from ..gesture_collection import GestureCollectionDraft
from .gesture_manager_view import GestureManagerView


class GestureManagerDialog:
    def __init__(self, master, gestures, on_create, on_save):
        self.master = master
        self.draft = GestureCollectionDraft(gestures)
        self.on_create = on_create
        self.on_save = on_save

    def show(self):
        self.modal = ModalDialog(
            self.master, "Manage Gestures", base_size=(900, 1200),
            minimum_size=(640, 480), on_close=self._request_close,
        )
        self.window = self.modal.window
        appearance = ThemeMetrics(self.window)
        self.guard = UnsavedChangesGuard(self.window)
        self.view = GestureManagerView(
            self.window, appearance, on_select=self._selection_changed,
            on_rename=self._name_changed, on_create=self._create, on_delete=self._delete,
            on_save=self._save_and_close, on_discard=self.window.destroy,
        )
        self.view.pack(fill="both", expand=True)
        self.view.show_collection(self.draft)
        self.modal.show(scale=appearance.scale)

    def _selection_changed(self, gesture_id):
        if gesture_id is None or gesture_id == self.draft.selected_id:
            return
        self.draft.select(gesture_id)
        self.view.show_name(self.draft.selected.name)

    def _name_changed(self):
        if self.draft.selected is not None:
            self.draft.rename(self.draft.selected_id, self.view.name.get())
            self.view.refresh_names(self.draft)

    def _create(self):
        try:
            gesture = self.on_create(self.draft.definitions)
            if gesture is not None:
                self.draft.add(gesture)
        except ValueError as error:
            messagebox.showerror("Cannot Create Gesture", str(error), parent=self.window)
            return
        if gesture is not None:
            self.view.show_collection(self.draft)
            self.view.entry.focus_set()
            self.view.entry.selection_range(0, "end")

    def _delete(self):
        if self.draft.selected is None or len(self.draft.definitions) <= 1:
            return
        if not messagebox.askyesno(
            "Delete Gesture", "Delete this gesture from the active profile?", parent=self.window,
        ):
            return
        self.draft.delete(self.draft.selected_id)
        self.view.show_collection(self.draft)

    def _save(self):
        try:
            self.on_save(self.draft.definitions, self.draft.selected_id)
        except (OSError, ValueError) as error:
            messagebox.showerror("Could Not Save Gestures", str(error), parent=self.window)
            return False
        return True

    def _save_and_close(self):
        if self._save():
            self.window.destroy()

    def _request_close(self):
        if self.guard.confirm(PendingChanges(
            "Gesture Manager", lambda: self.draft.is_dirty, self._save, self.draft.discard,
        ), return_label="Cancel"):
            self.window.destroy()
