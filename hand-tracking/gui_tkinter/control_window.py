"""Application hub hosting shared settings and independent tracking windows."""

import tkinter as tk

from .components.theme import apply_theme, resolve_scale
from .core.input_interactions import InputInteractionController
from .core.state import ControlWindowContext
from .core.window_shell import WindowShell


class ControlWindow:
    def __init__(self, context: ControlWindowContext):
        self.context = context
        self._on_quit = context.callbacks.on_close
        context.callbacks.on_close = self._close_hub
        self._display = None
        root = tk.Tk()
        root.withdraw()
        self.shell = WindowShell(
            root, context, title="Tracking hub", main_title="Main", base_size=(860, 720),
        )
        self.shell.view.default_callback_exception = root.report_callback_exception
        root.report_callback_exception = self._report_callback_exception
        context.tracking_modules.attach(root)
        self.apply_display(context.settings.data)
        self.shell.build()
        self.interactions = InputInteractionController(root)
        self.interactions.bind()
        root.deiconify()

    def apply_display(self, data):
        root = self.shell.view.root
        scale = resolve_scale(root, data.ui_scale)
        display = (data.theme, scale)
        if display != self._display:
            apply_theme(root, data.theme, scale)
            if self._display is None or self._display[1] != scale:
                self.shell.geometry.resize(scale)
                self.context.tracking_modules.resize(scale)
            self._display = display

    def confirm_pending_changes(self):
        return self.shell.lifecycle.confirm_close() and self.context.tracking_modules.confirm_close()

    def _close_hub(self):
        if self.context.tracking_modules.confirm_close():
            self._on_quit()

    def _report_callback_exception(self, exception, value, traceback):
        if issubclass(exception, KeyboardInterrupt):
            self._on_quit()
        else:
            self.shell.view.default_callback_exception(exception, value, traceback)

    def after(self, delay_ms, callback):
        return self.shell.view.root.after(delay_ms, callback)

    def run(self):
        self.shell.view.root.mainloop()

    def quit(self):
        self.shell.view.root.quit()

    def close(self):
        self.context.tracking_modules.close()
        self.shell.view.root.destroy()
