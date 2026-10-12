from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from gestures.gesture_config import ensure_default_gesture_profile
from gestures.profile_manager import GestureProfileManager


class GestureProfilePickerDialog:
    """Folder browser and profile selector for the active gesture mapping."""

    def __init__(self, parent, initial_folder, active_profile, on_create_profile=None):
        self.parent = parent
        self.active_profile = Path(active_profile) if active_profile else None
        self.on_create_profile = on_create_profile
        self.folder = Path(initial_folder)
        self.profiles = ()
        self.result = None

        self.window = tk.Toplevel(parent)
        self.window.title("Choose Gesture Profile")
        self.window.transient(parent)
        self.window.resizable(False, False)
        self.window.geometry("640x480")
        self.window.minsize(640, 480)
        self.window.protocol("WM_DELETE_WINDOW", self._cancel)

        body = ttk.Frame(self.window, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(
            body, text="Choose a folder, then select a gesture profile."
        ).pack(anchor="w", pady=(0, 10))

        folder_row = ttk.Frame(body)
        folder_row.pack(fill="x", pady=(0, 10))
        self.folder_var = tk.StringVar()
        ttk.Entry(folder_row, textvariable=self.folder_var, state="readonly").pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(folder_row, text="Browse...", command=self._browse_folder).pack(
            side="left", padx=(8, 0)
        )

        profiles_header = ttk.Frame(body)
        profiles_header.pack(fill="x", pady=(2, 8))
        ttk.Label(
            profiles_header, text="Available profiles",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(side="left")
        ttk.Button(
            profiles_header, text="Create profile...", command=self._create_profile
        ).pack(side="right")

        list_frame = ttk.Frame(body)
        list_frame.pack(fill="both", expand=True)
        profile_style = ttk.Style(self.window)
        profile_style.configure("GestureProfiles.Treeview", rowheight=42)
        self.profile_list = ttk.Treeview(
            list_frame, show="tree", height=8,
            selectmode="browse", style="GestureProfiles.Treeview",
        )
        self.profile_list.column("#0", anchor="w", width=560)
        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.profile_list.yview
        )
        self.profile_list.configure(yscrollcommand=scrollbar.set)
        self.profile_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.profile_list.bind("<<TreeviewSelect>>", self._selection_changed)
        self.profile_list.bind("<Double-1>", self._confirm)

        self.status_var = tk.StringVar()
        ttk.Label(body, textvariable=self.status_var).pack(anchor="w", pady=(8, 0))
        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self._cancel).pack(side="right")
        self.confirm_button = ttk.Button(
            buttons, text="Use selected profile", command=self._confirm,
            style="Accent.TButton",
        )
        self.confirm_button.pack(side="right", padx=(0, 8))
        self.confirm_button.state(["disabled"])

        self._load_folder(self.folder)

    def show(self):
        self._center()
        self.window.wait_visibility()
        self.window.grab_set()
        self.window.wait_window()
        return self.result

    def _center(self):
        self.window.update_idletasks()
        width, height = self.window.winfo_reqwidth(), self.window.winfo_reqheight()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - width) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - height) // 2
        self.window.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _load_folder(self, folder):
        try:
            folder = Path(folder)
            ensure_default_gesture_profile(folder)
            self.profiles = GestureProfileManager.list_profiles(folder)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Could not read profile folder", str(error), parent=self.window
            )
            return

        self.folder = folder
        self.folder_var.set(str(folder))
        for item in self.profile_list.get_children():
            self.profile_list.delete(item)
        for index, profile in enumerate(self.profiles):
            self.profile_list.insert(
                "", "end", iid=str(index), text=profile.name
            )
            if (
                self.active_profile is not None
                and profile.resolve() == self.active_profile.resolve()
            ):
                self.profile_list.selection_set(str(index))
                self.profile_list.focus(str(index))
                self.profile_list.see(str(index))
        if self.profiles:
            self.status_var.set(f"{len(self.profiles)} profile(s) found")
        else:
            self.status_var.set("No valid profiles found in this folder")
        self._selection_changed()

    def _browse_folder(self):
        selected = filedialog.askdirectory(
            parent=self.window,
            initialdir=str(self.folder),
            title="Choose gesture profile folder",
        )
        if selected:
            self.active_profile = None
            self._load_folder(selected)

    def _selection_changed(self, _event=None):
        if self.profile_list.selection():
            self.confirm_button.state(["!disabled"])
        else:
            self.confirm_button.state(["disabled"])

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
        self.active_profile = Path(profile)
        self._load_folder(self.folder)

    def _confirm(self, _event=None):
        selected = self.profile_list.selection()
        if not selected:
            return
        self.result = (self.profiles[int(selected[0])], self.folder)
        self.window.destroy()

    def _cancel(self):
        self.window.destroy()
