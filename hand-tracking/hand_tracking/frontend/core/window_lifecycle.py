"""Visibility, tab transitions, and unsaved changes for any panel window."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .unsaved_changes_guard import PendingChanges, UnsavedChangesGuard
from .idle_refresh import IdleRefresh
from .state import WindowContext, WindowView


class WindowLifecycleController:
    def __init__(
        self, view: WindowView, context: WindowContext, *,
        changes_guard: UnsavedChangesGuard | None = None,
    ) -> None:
        self.view = view
        self.context = context
        self._notified_active = None
        self.activity_refresh = IdleRefresh(view.root, self.notify_activity)
        self.focus_refresh = IdleRefresh(view.root, self._clear_page_focus)
        self.changes_guard = (
            changes_guard if changes_guard is not None else UnsavedChangesGuard(view.root)
        )
        settings = context.panels.settings
        self.editable_pages = {
            str(view.settings_tab): PendingChanges(
                "Settings", settings.is_dirty, settings.apply, settings.discard,
            ),
        }
        mapping = context.panels.mapping
        if mapping is not None:
            self.editable_pages[str(view.mapping_tab)] = PendingChanges(
                "Mapping", mapping.is_dirty, mapping.save, mapping.discard,
            )

    def bind(self) -> None:
        self.view.current_tab = self.view.notebook.select()
        self.view.notebook.before_select = self._before_tab_change
        self.view.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.view.root.protocol("WM_DELETE_WINDOW", self.request_close)
        self.view.root.bind("<Map>", self._visibility_changed, add="+")
        self.view.root.bind("<Unmap>", self._visibility_changed, add="+")
        self.activity_refresh.schedule()

    def _before_tab_change(self, current_tab: str, _target_tab: str) -> bool:
        changes = self.editable_pages.get(current_tab)
        return changes is None or self.changes_guard.confirm(changes)

    def _on_tab_changed(self, _event: tk.Event[tk.Misc]) -> None:
        self.view.current_tab = self.view.notebook.select()
        self.notify_activity()
        self.focus_refresh.schedule()

    def _clear_page_focus(self) -> None:
        """Clear an auto-focused page input without activating another window."""
        window = self.view.root
        focused = window.focus_get()
        if (
            focused is not None
            and focused.winfo_toplevel() is window
            and focused not in (window, self.view.notebook)
        ):
            window.focus_set()

    def _visibility_changed(self, event: tk.Event[tk.Misc]) -> None:
        if event.widget is self.view.root:
            self.activity_refresh.schedule()

    def page_visible(self, page: ttk.Frame) -> bool:
        return bool(self.view.root.winfo_viewable()) and self.view.notebook.select() == str(page)

    def notify_activity(self) -> None:
        callback = self.context.callbacks.on_main_active
        active = self.page_visible(self.view.main_tab)
        if callback and active != self._notified_active:
            self._notified_active = active
            callback(active)

    def confirm_close(self) -> bool:
        return all(
            self.changes_guard.confirm(changes, return_label="Cancel")
            for changes in self.editable_pages.values()
        )

    def request_close(self) -> None:
        if self.confirm_close():
            self.context.callbacks.on_close()
