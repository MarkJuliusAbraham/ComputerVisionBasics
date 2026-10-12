"""Shared gesture management actions for the browser and dedicated manager."""

from dataclasses import replace
from tkinter import messagebox

from .dialogs import GestureManagerDialog, GestureRenameDialog


class GestureManagementActions:
    def __init__(self, parent, session, *, before_edit, on_save, segment_count):
        self.parent = parent
        self.session = session
        self.before_edit = before_edit
        self.on_save = on_save
        self.segment_count = segment_count

    def manage(self):
        self.before_edit()
        GestureManagerDialog(
            self.parent.winfo_toplevel(), gestures=self.session.definitions,
            on_create=self._create, on_save=self.on_save,
        ).show()

    def _create(self, definitions):
        return self.session.create_gesture(
            definitions, self.segment_count(), self.session.config.reset_match,
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
        definitions = tuple(
            replace(item, name=name) if item.id == gesture_id else item
            for item in self.session.definitions
        )
        self.on_save(definitions, gesture_id)

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
        remaining = tuple(item for item in definitions if item.id != gesture_id)
        selected_id = remaining[min(index, len(remaining) - 1)].id
        try:
            self.on_save(remaining, selected_id)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Could not delete gesture", str(error), parent=self.parent.winfo_toplevel(),
            )
