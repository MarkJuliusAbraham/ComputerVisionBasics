"""Shared gesture management actions for the browser and dedicated manager."""

from tkinter import messagebox
from gestures.gesture_factory import GestureFactory

from .dialogs import GestureManagerDialog, GestureRenameDialog
from .gesture_collection import GestureCollectionDraft


class GestureManagementActions:
    def __init__(self, parent, session, *, before_edit, on_save, segment_count, gesture_factory=None):
        self.parent = parent
        self.session = session
        self.before_edit = before_edit
        self.on_save = on_save
        self.segment_count = segment_count
        self.gesture_factory = gesture_factory if gesture_factory is not None else GestureFactory()

    def manage(self):
        self.before_edit()
        GestureManagerDialog(
            self.parent.winfo_toplevel(), gestures=self.session.definitions,
            on_create=self._create, on_save=self.on_save,
        ).show()

    def _create(self, definitions):
        return self.gesture_factory.create(
            definitions, self.segment_count(), self.session.config.reset_match,
            repeat_settings=self.session.config.repeat_settings,
        )

    def rename(self, gesture_id):
        definition = next(
            (item for item in self.session.definitions if item.id == gesture_id), None,
        )
        if definition is None:
            return
        self.before_edit()
        GestureRenameDialog(
            self.parent.winfo_toplevel(), definition.name,
            on_save=lambda name: self._save_name(gesture_id, name),
        ).show()

    def _save_name(self, gesture_id, name):
        if not any(item.id == gesture_id for item in self.session.definitions):
            raise ValueError("This gesture is no longer in the active profile")
        draft = GestureCollectionDraft(self.session.definitions)
        draft.rename(gesture_id, name)
        self.on_save(draft.definitions, draft.selected_id)

    def delete(self, gesture_id):
        definitions = self.session.definitions
        if len(definitions) <= 1:
            return
        index = next((i for i, item in enumerate(definitions) if item.id == gesture_id), None)
        if index is None:
            return
        self.before_edit()
        if not messagebox.askyesno(
            "Delete gesture", f'Delete "{definitions[index].name}" from the active profile?',
            parent=self.parent.winfo_toplevel(),
        ):
            return
        draft = GestureCollectionDraft(definitions)
        draft.delete(gesture_id)
        try:
            self.on_save(draft.definitions, draft.selected_id)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Could not delete gesture", str(error), parent=self.parent.winfo_toplevel(),
            )
