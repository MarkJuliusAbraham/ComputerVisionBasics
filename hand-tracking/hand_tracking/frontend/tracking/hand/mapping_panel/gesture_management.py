"""Shared gesture management actions for the browser and dedicated manager."""

from tkinter import messagebox
from hand_tracking.backend.gestures.gesture_config import find_definition
from hand_tracking.backend.gestures.gesture_factory import GestureFactory

from .dialogs.gesture_manager_dialog import GestureManagerDialog
from .dialogs.gesture_rename_dialog import GestureRenameDialog
from .gesture_collection import MISSING_GESTURE, GestureCollectionDraft


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
        definition = find_definition(self.session.definitions, gesture_id)
        if definition is None:
            return
        self.before_edit()
        GestureRenameDialog(
            self.parent.winfo_toplevel(), definition.name,
            on_save=lambda name: self._save_name(gesture_id, name),
        ).show()

    def _save_name(self, gesture_id, name):
        if find_definition(self.session.definitions, gesture_id) is None:
            raise ValueError(MISSING_GESTURE)
        draft = GestureCollectionDraft(self.session.definitions)
        draft.rename(gesture_id, name)
        self.on_save(draft.definitions, draft.selected_id)

    def delete(self, gesture_id):
        definitions = self.session.definitions
        definition = find_definition(definitions, gesture_id)
        if len(definitions) <= 1 or definition is None:
            return
        self.before_edit()
        if not messagebox.askyesno(
            "Delete gesture", f'Delete "{definition.name}" from the active profile?',
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
