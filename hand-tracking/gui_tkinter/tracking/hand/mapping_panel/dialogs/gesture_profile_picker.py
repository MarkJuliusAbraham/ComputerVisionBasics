"""Folder discovery and explicit confirmation of a gesture profile."""

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from gestures.gesture_config import ensure_default_gesture_profile
from gestures.profile_manager import GestureProfileManager

from .profile_picker_view import ProfilePickerView


class GestureProfilePickerDialog:
    """Connect profile discovery and creation to the picker view."""

    def __init__(self, parent, initial_folder, active_profile, on_create_profile=None):
        self.parent = parent
        self.active_profile = Path(active_profile) if active_profile else None
        self.on_create_profile = on_create_profile
        self.folder = Path(initial_folder)
        self.result = None

        self.window = tk.Toplevel(parent)
        self.window.title("Gesture profiles")
        self.window.transient(parent)
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self._cancel)
        self.window.bind("<Escape>", lambda _event: self._cancel())
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
        self._center()
        if not self.window.winfo_viewable():
            self.window.wait_visibility()
        self.window.grab_set()
        self.window.wait_window()
        return self.result

    def _center(self):
        self.window.update_idletasks()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        margin = round(16 * self.view.scale)
        preferred_width, preferred_height = self.view.preferred_size
        width = min(preferred_width, max(1, screen_width - 2 * margin))
        height = min(preferred_height, max(1, screen_height - margin - 48))
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - width) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - height) // 2
        x = max(margin, min(x, screen_width - width - margin))
        y = max(margin, min(y, screen_height - height - 48))
        self.window.geometry(f"{width}x{height}+{x}+{y}")

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

