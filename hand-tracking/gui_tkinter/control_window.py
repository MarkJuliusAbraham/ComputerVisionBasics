import tkinter as tk
from tkinter import ttk

from .core.state import ControlWindowContext, WindowView
from .core.window_lifecycle import WindowLifecycleController

BASE_SIZE = (860, 720)  # window size in pixels at 100%

class ControlWindow:
    """Control panel with Main and Settings tabs."""

    def __init__(self, context: ControlWindowContext):
        self.context = context
        self._configure_panels()
        self.view = self._create_view()
        self._build_panels()
        self._bind_events()

    def _configure_panels(self):
        """Connect panel callbacks without making panels depend on the shell."""
        context = self.context
        context.panels.settings.on_settings_path = (
            context.callbacks.on_settings_path
        )
        if (
            getattr(context.panels.settings, "on_apply", None) is None
            and context.callbacks.on_apply
        ):
            context.panels.settings.on_apply = context.callbacks.on_apply

    def _create_view(self):
        """Create the window and its notebook tab containers."""
        root = tk.Tk()
        root.title("Controls")
        root.resizable(False, False)

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text="Main")
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text="Settings")

        mapping_tab = None
        if self.context.panels.mapping is not None:
            mapping_tab = ttk.Frame(notebook)
            notebook.add(mapping_tab, text="Mapping")
            build = getattr(self.context.panels.mapping, "build", None)
            if build is None:
                raise TypeError("mapping_panel must provide a build(parent) method")
            build(mapping_tab)

        view = WindowView(
            root=root,
            notebook=notebook,
            main_tab=main_tab,
            settings_tab=settings_tab,
            mapping_tab=mapping_tab,
            default_callback_exception=root.report_callback_exception,
        )
        root.report_callback_exception = self._report_callback_exception
        return view

    def _build_panels(self):
        """Mount the main and settings panel implementations into their tabs."""
        context = self.context
        settings = context.settings
        context.panels.main.build(
            self.view.main_tab,
            on_restart=context.callbacks.on_restart,
            on_close=context.callbacks.on_close,
            camera_index=context.camera_index,
            on_camera_switch=context.callbacks.on_camera_switch,
            on_toggle_tracking=context.callbacks.on_toggle_tracking,
            theme_name=settings.data.theme,
            max_deviation=settings.data.finger_classification_thresholds[-1],
        )
        build = getattr(context.panels.settings, "build", None)
        if build is None:
            raise TypeError("settings_panel must provide a build(parent, settings) method")
        build(self.view.settings_tab, settings)

    def _bind_events(self):
        """Install notebook and window lifecycle callbacks after mounting panels."""
        self.lifecycle = WindowLifecycleController(self.view, self.context)
        self.lifecycle.bind()

    def _report_callback_exception(self, exception, value, traceback):
        """Treat IDE shutdown interrupts as a request to close the application."""
        if issubclass(exception, KeyboardInterrupt):
            self.context.callbacks.on_close()
            return
        self.view.default_callback_exception(exception, value, traceback)

    def after(self, delay_ms, callback):
        self.view.root.after(delay_ms, callback)

    def run(self):
        self.view.root.mainloop()

    def quit(self):
        self.view.root.quit()

    def close(self):
        self.view.root.destroy()
