"""A fixed, parent-relative modal window with safe nested grab ownership."""

import tkinter as tk

from .window_geometry import WindowGeometry


class ModalDialog:
    def __init__(self, parent, title, *, base_size=None, minimum_size=(320, 180), on_close=None):
        self.parent = parent.winfo_toplevel()
        self.window = tk.Toplevel(self.parent)
        self.window.withdraw()
        self.window.title(title)
        self.window.transient(self.parent)
        self.window.resizable(False, False)
        self.geometry = (
            WindowGeometry(self.window, base_size, minimum_size=minimum_size)
            if base_size is not None else None
        )
        close = on_close if on_close is not None else self.window.destroy
        self.window.protocol("WM_DELETE_WINDOW", close)
        self.window.bind("<Escape>", lambda _event: close())

    def show(self, *, scale=1.0, initial_focus=None):
        """Show only after construction and restore a containing dialog's grab."""
        previous_grab = self.window.grab_current()
        try:
            if self.geometry is not None:
                self.geometry.resize(scale)
                self.geometry.center_over(self.parent)
            else:
                WindowGeometry(self.window, (1, 1)).center_over(self.parent, requested=True)
            self.window.deiconify()
            self.window.wait_visibility()
            self.window.grab_set()
            (initial_focus if initial_focus is not None else self.window).focus_set()
            self.window.wait_window()
        finally:
            if previous_grab is not None:
                try:
                    if previous_grab.winfo_exists():
                        previous_grab.grab_set()
                except tk.TclError:
                    pass  # Its owning window can close while this dialog is open.
