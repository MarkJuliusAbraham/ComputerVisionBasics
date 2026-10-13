"""Visibility, tab transitions, and unsaved changes for any panel window."""

from .unsaved_changes_guard import PendingChanges, UnsavedChangesGuard
from .idle_refresh import IdleRefresh


class WindowLifecycleController:
    def __init__(self, view, context, *, changes_guard=None):
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

    def bind(self):
        self.view.current_tab = self.view.notebook.select()
        self.view.notebook.before_select = self._before_tab_change
        self.view.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.view.root.protocol("WM_DELETE_WINDOW", self.request_close)
        self.view.root.bind("<Map>", self._visibility_changed, add="+")
        self.view.root.bind("<Unmap>", self._visibility_changed, add="+")
        self.activity_refresh.schedule()

    def _before_tab_change(self, current_tab, _target_tab):
        changes = self.editable_pages.get(current_tab)
        return changes is None or self.changes_guard.confirm(changes)

    def _on_tab_changed(self, _event):
        self.view.current_tab = self.view.notebook.select()
        self.notify_activity()
        self.focus_refresh.schedule()

    def _clear_page_focus(self):
        """Clear an auto-focused page input without activating another window."""
        window = self.view.root
        focused = window.focus_get()
        if (
            focused is not None
            and focused.winfo_toplevel() is window
            and focused not in (window, self.view.notebook)
        ):
            window.focus_set()

    def _visibility_changed(self, event):
        if event.widget is self.view.root:
            self.activity_refresh.schedule()

    def page_visible(self, page):
        return bool(self.view.root.winfo_viewable()) and self.view.notebook.select() == str(page)

    def notify_activity(self):
        callback = self.context.callbacks.on_main_active
        active = self.page_visible(self.view.main_tab)
        if callback and active != self._notified_active:
            self._notified_active = active
            callback(active)

    def confirm_close(self):
        return all(
            self.changes_guard.confirm(changes, return_label="Cancel")
            for changes in self.editable_pages.values()
        )

    def request_close(self):
        if self.confirm_close():
            self.context.callbacks.on_close()
