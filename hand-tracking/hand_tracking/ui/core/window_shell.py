"""Notebook composition reusable across independent tracking modules."""

from tkinter import ttk
from dataclasses import replace
import tkinter as tk

from hand_tracking.ui.components.guarded_notebook import GuardedNotebook

from .state import WindowContext, WindowView
from .window_geometry import WindowGeometry
from .window_lifecycle import WindowLifecycleController


class WindowShell:
    def __init__(
        self, window: tk.Tk | tk.Toplevel, context: WindowContext, *,
        title: str, main_title: str, base_size: tuple[int, int],
    ) -> None:
        self.context = context
        window.title(title)
        notebook = GuardedNotebook(window)
        notebook.pack(fill="both", expand=True)
        main = ttk.Frame(notebook)
        settings = ttk.Frame(notebook)
        notebook.add(main, text=main_title)
        notebook.add(settings, text="Settings")
        mapping = None
        if context.panels.mapping is not None:
            mapping = ttk.Frame(notebook)
            notebook.add(mapping, text="Mapping")
        self.view = WindowView(window, notebook, main, settings, mapping)
        self.geometry = WindowGeometry(window, base_size)
        self.lifecycle = WindowLifecycleController(self.view, context)

    def build(self) -> None:
        panels = self.context.panels
        callbacks = self.context.callbacks
        panels.main.build(
            self.view.main_tab, callbacks=replace(callbacks, on_close=self.lifecycle.request_close),
            settings=self.context.settings.data, camera_index=self.context.camera_index,
        )
        panels.settings.on_settings_path = callbacks.on_settings_path
        if panels.settings.on_apply is None:
            panels.settings.on_apply = callbacks.on_apply
        panels.settings.build(self.view.settings_tab, self.context.settings)
        if panels.mapping is not None:
            mapping_tab = self.view.mapping_tab
            assert mapping_tab is not None
            panels.mapping.build(mapping_tab)
        self.lifecycle.bind()
