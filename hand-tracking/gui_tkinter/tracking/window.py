"""A persistent, non-modal workspace window for one tracking module."""

import tkinter as tk

from gui_tkinter.components.theme import resolve_scale
from gui_tkinter.core.window_shell import WindowShell


class TrackingWindow:
    def __init__(self, parent, context, title):
        window = tk.Toplevel(parent)
        window.withdraw()
        context.callbacks.on_close = self.hide
        self.shell = WindowShell(
            window, context, title=title, main_title="Debugging", base_size=(1040, 780),
        )
        self.shell.build()
        self.shell.geometry.resize(resolve_scale(parent, context.settings.data.ui_scale))
        self.shell.geometry.place_near(parent)

    def show(self):
        window = self.shell.view.root
        window.deiconify()
        window.lift()
        window.focus_set()
        self.shell.lifecycle.notify_activity()

    def hide(self):
        self.shell.view.root.withdraw()
        self.shell.lifecycle.notify_activity()

    def show_settings(self):
        self.shell.view.notebook.select(self.shell.view.settings_tab)

    def request_close(self):
        self.shell.lifecycle.request_close()

    def confirm_close(self):
        return self.shell.lifecycle.confirm_close()

    @property
    def preview_visible(self):
        return self.shell.lifecycle.page_visible(self.shell.view.settings_tab)

    def resize(self, scale):
        self.shell.geometry.resize(scale)

    def close(self):
        self.shell.view.root.destroy()
