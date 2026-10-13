"""Coordinator for profile selection, gesture editing, and mapping saves."""

from tkinter import ttk

from gui_tkinter.components.unapplied_changes_dialog import UnappliedChangesDialog

from .dialogs import GestureProfilePickerDialog, ResetGestureDialog
from .gesture_management import GestureManagementActions
from .mapping_form import MappingForm
from .mapping_session import MappingSession


class MappingEditor(ttk.Frame):
    """Connect the form and its editing session to application callbacks."""

    def __init__(self, master, on_saved=None, config_path=None, segment_count=4):
        super().__init__(master)
        self.on_saved = on_saved
        self.session = MappingSession(config_path=config_path)
        self._shown_id = next(iter(self.session.drafts), None)
        self.gesture_management = GestureManagementActions(
            self, self.session, before_edit=self._capture_draft,
            on_save=self._save_managed_gestures, segment_count=lambda: self.form.segment_count,
        )
        self.form = MappingForm(
            self,
            on_change=self._editor_changed,
            on_repeat_change=self._repeat_changed,
            on_select=self._selection_changed,
            on_manage=self.gesture_management.manage,
            on_rename=self.gesture_management.rename,
            on_delete=self.gesture_management.delete,
            on_choose_profile=self._choose_profile,
            on_edit_reset=self._edit_reset,
            on_save=self.save,
            on_discard=self.discard,
            segment_count=segment_count,
        )
        self.form.pack(fill="both", expand=True)
        self._refresh_form()

    def _capture_draft(self):
        if self._shown_id is not None:
            self.session.update_draft(self._shown_id, self.form.values())
        self.session.update_reset(self.form.reset_values())

    def _refresh_form(self, selected_id=None):
        if selected_id in self.session.drafts:
            self._shown_id = selected_id
        if self._shown_id not in self.session.drafts:
            self._shown_id = next(iter(self.session.drafts), None)
        self.form.show_profile(self.session.config_path)
        self.form.show_gestures(
            self.session.definitions, self._shown_id, validation=self.session.validation_report,
        )
        if self._shown_id is not None:
            self.form.load_draft(self.session.drafts[self._shown_id])
        self.form.load_reset(self.session.reset_draft)
        self._refresh_feedback()

    def _refresh_feedback(self):
        self.form.set_dirty(self.session.is_dirty)
        self.form.show_validation(self.session.validation_report)

    def set_segment_count(self, segment_count):
        self._capture_draft()
        self.form.set_segment_count(segment_count)
        self._refresh_feedback()

    def _editor_changed(self):
        self._capture_draft()
        self._refresh_feedback()

    def _repeat_changed(self):
        self._capture_draft()
        if self.form.applies_repeats_to_all():
            self.session.apply_repeats_to_all(self.form.repeat_values())
        self._refresh_feedback()

    def _selection_changed(self, gesture_id):
        self._capture_draft()
        self._shown_id = gesture_id
        self.form.show_selected_gesture(gesture_id)
        self.form.load_draft(self.session.drafts[gesture_id])
        self._refresh_feedback()

    def is_dirty(self):
        self._capture_draft()
        return self.session.is_dirty

    def discard(self):
        self.session.discard()
        self._refresh_form()
        self.form.set_status("Unsaved mapping changes discarded")

    def save(self):
        self._capture_draft()
        self._refresh_feedback()
        try:
            config = self.session.save()
        except (ValueError, OSError) as error:
            self.form.set_status(f"Could not save mappings: {error}")
            return False
        self._refresh_form()
        self.form.set_status("Gesture mappings saved")
        self._notify_saved(config)
        return True

    def _edit_reset(self):
        self._capture_draft()
        ResetGestureDialog(
            self.winfo_toplevel(), self.session.reset_draft, self.form.segment_count,
            on_use_changes=self._stage_reset,
        ).show()

    def _stage_reset(self, match):
        self.session.update_reset(match)
        self.form.load_reset(match)
        self._refresh_feedback()
        self.form.set_status("Reset gesture changes staged. Save mappings to commit.")

    def _save_managed_gestures(self, staged_definitions, selected_id=None):
        config = self.session.save_managed_gestures(staged_definitions)
        self._refresh_form(selected_id=selected_id)
        self.form.set_status(
            "Gestures saved; mapping edits remain unsaved"
            if self.session.is_dirty else "Gestures saved"
        )
        self._notify_saved(config)

    def _confirm_profile_change(self):
        if not self.is_dirty():
            return True
        choice = UnappliedChangesDialog(
            self.winfo_toplevel(), context="Mapping", action_label="Save"
        ).show()
        if choice == "save":
            return self.save()
        if choice == "discard":
            self.discard()
            return True
        return False

    def _activate_profile(self, path):
        if not self._confirm_profile_change():
            return False
        try:
            config = self.session.activate_profile(path)
        except (ValueError, OSError) as error:
            self.form.set_status(f"Could not load profile: {error}")
            return False
        self._shown_id = None
        self._refresh_form()
        self.form.set_status(f"Active profile: {self.session.config_path.name}")
        self._notify_saved(config)
        return True

    def _choose_profile(self):
        dialog = GestureProfilePickerDialog(
            self.winfo_toplevel(),
            initial_folder=self.session.profile_folder,
            active_profile=self.session.config_path,
            on_create_profile=self._create_profile_in_folder,
        )
        selection = dialog.show()
        if selection is not None:
            profile, _folder = selection
            self._activate_profile(profile)

    def _create_profile_in_folder(self, folder, profile_name):
        self._capture_draft()
        return self.session.create_profile(folder, profile_name)

    def _notify_saved(self, config):
        if self.on_saved:
            self.on_saved(config)
