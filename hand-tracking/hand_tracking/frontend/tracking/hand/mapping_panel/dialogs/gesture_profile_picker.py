"""Folder discovery and explicit confirmation of a gesture profile."""

from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

from hand_tracking.backend.gestures.gesture_config import ensure_default_gesture_profile
from hand_tracking.backend.gestures.profile_manager import GestureProfileManager
from hand_tracking.frontend.core.modal_dialog import ModalDialog

from .profile_picker_view import ProfilePickerView


class GestureProfilePickerDialog:
    """Connect profile discovery and creation to the picker view."""

    def __init__(self, parent, initial_folder, active_profile, on_create_profile=None):
        self.parent = parent
        self.active_profile = Path(active_profile) if active_profile else None
        self.on_create_profile = on_create_profile
        self.folder = Path(initial_folder)
        self.result = None

        self.modal = ModalDialog(parent, "Gesture profiles", base_size=(720, 560), on_close=self._cancel)
        self.window = self.modal.window
        self.view = ProfilePickerView(
            self.window,
            on_browse=self._browse_folder,
            on_create=self._create_profile if on_create_profile else None,
            on_confirm=self._confirm,
            on_cancel=self._cancel,
        )
        self.view.pack(fill="both", expand=True)
        self._load_folder(self.folder)

    def show(self):
        self.modal.show(scale=self.view.appearance.scale)
        return self.result

    def _load_folder(self, folder, selected_profile=None):
        try:
            folder = Path(folder)
            ensure_default_gesture_profile(folder)
            profiles = GestureProfileManager.list_profiles(folder)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Could not read profile folder", str(error), parent=self.window
            )
            return

        self.folder = folder
        self.view.show_folder(folder, profiles, self.active_profile, selected_profile)

    def _browse_folder(self):
        selected = filedialog.askdirectory(
            parent=self.window,
            initialdir=str(self.folder),
            title="Choose gesture profile folder",
        )
        if selected:
            self._load_folder(selected)

    def _create_profile(self):
        if not self.on_create_profile:
            return
        name = simpledialog.askstring(
            "Create gesture profile", "Profile name:", parent=self.window
        )
        if not name:
            return
        profile_name = "_".join(name.strip().split())
        if not profile_name or any(char in profile_name for char in '<>:\\"/|?*'):
            messagebox.showerror(
                "Invalid profile name", "Enter a valid file name.", parent=self.window
            )
            return
        try:
            profile = self.on_create_profile(self.folder, profile_name)
        except (ValueError, OSError) as error:
            messagebox.showerror(
                "Could not create profile", str(error), parent=self.window
            )
            return
        self._load_folder(self.folder, selected_profile=profile)

    def _confirm(self):
        selected = self.view.selected_profile
        if selected is None:
            return
        self.result = (selected, self.folder)
        self.window.destroy()

    def _cancel(self):
        self.window.destroy()
