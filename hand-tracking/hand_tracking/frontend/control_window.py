"""Application hub hosting shared settings and independent tracking windows."""

import tkinter as tk
import logging
from contextlib import ExitStack
from collections.abc import Callable
from tkinter import messagebox
from types import TracebackType
from hand_tracking.backend.settings.settings_manager import SettingsData

from .components.theme import ThemeColors, apply_theme, resolve_scale
from .components.themes.title_bar import TitleBarTheme
from .core.input_interactions import InputInteractionController
from .core.state import ControlWindowContext
from .core.window_shell import WindowShell


class ControlWindow:
    def __init__(self, context: ControlWindowContext) -> None:
        self.context = context
        self._on_quit = context.callbacks.on_close
        context.callbacks.on_close = self._close_hub
        self._display = None
        with ExitStack() as startup:
            root = tk.Tk()
            startup.callback(root.destroy)
            root.withdraw()
            # Native title-bar coloring, where the platform has it, for every window of this root.
            TitleBarTheme.for_root(
                root, lambda: ThemeColors(root).title_bar, context.platform.create_title_bar_style(),
            )
            self.shell = WindowShell(
                root, context, title="Tracking hub", main_title="Main", base_size=(860, 720),
            )
            root.report_callback_exception = self._report_callback_exception
            context.tracking_modules.attach(root)
            self.apply_display(context.settings.data)
            self.shell.build()
            self.interactions = InputInteractionController(root)
            self.interactions.bind()
            root.deiconify()
            startup.pop_all()

    def apply_display(self, data: SettingsData) -> None:
        root = self.shell.view.root
        scale = resolve_scale(root, data.ui_scale)
        display = (data.theme, scale)
        if display != self._display:
            apply_theme(root, data.theme, scale)
            if self._display is None or self._display[1] != scale:
                self.shell.geometry.resize(scale)
                self.context.tracking_modules.resize(scale)
            self._display = display

    def confirm_pending_changes(self) -> bool:
        return self.shell.lifecycle.confirm_close() and self.context.tracking_modules.confirm_close()

    def _close_hub(self) -> None:
        if self.context.tracking_modules.confirm_close():
            self._on_quit()

    def _report_callback_exception(
        self, exception: type[BaseException], value: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        if issubclass(exception, KeyboardInterrupt):
            self._on_quit()
        else:
            self._on_quit()
            logging.getLogger(__name__).error(
                "Unhandled window callback exception", exc_info=(exception, value, traceback),
            )
            try:
                self.show_failure(str(value) or exception.__name__)
            except Exception:
                logging.getLogger(__name__).exception("Could not display the callback failure")

    @property
    def window_parent(self) -> tk.Misc:
        """The Tk root other windows, such as a Tk camera preview, belong to."""
        return self.shell.view.root

    def after(self, delay_ms: int, callback: Callable[[], None]) -> str:
        return self.shell.view.root.after(delay_ms, callback)

    def after_cancel(self, identifier: str) -> None:
        self.shell.view.root.after_cancel(identifier)

    def run(self) -> None:
        self.shell.view.root.mainloop()

    def quit(self) -> None:
        self.shell.view.root.quit()

    def close(self) -> None:
        try:
            self.context.tracking_modules.close()
        finally:
            self.shell.view.root.destroy()

    def hide_overlays(self) -> None:
        self.context.tracking_modules.hide_overlays()

    def show_failure(self, error_message: str) -> None:
        messagebox.showerror(
            "Tracking stopped",
            f"{error_message}\n\nThe application will close. "
            "See logs/application.log for details.",
            parent=self.shell.view.root,
        )
