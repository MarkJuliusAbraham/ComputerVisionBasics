"""Window lifecycle coordination for the Tkinter control surface."""

from gui_tkinter.components.unapplied_changes_dialog import UnappliedChangesDialog


class WindowLifecycleController:
    """Own notebook transitions and close confirmation for the control window."""

    def __init__(self, view, context):
        self.view = view
        self.context = context

    def bind(self):
        self.view.current_tab = self.view.notebook.select()
        self.view.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.view.root.protocol("WM_DELETE_WINDOW", self.request_close)

    def _on_tab_changed(self, event):
        old_tab = self.view.current_tab
        new_tab = self.view.notebook.select()
        self.view.current_tab = new_tab

        leaving_settings = (
            old_tab == str(self.view.settings_tab) and new_tab != old_tab
        )
        if leaving_settings and self.context.panels.settings.is_dirty():
            if not self._confirm_leave():
                self.view.current_tab = old_tab
                self.view.notebook.select(old_tab)

        callback = self.context.callbacks.on_tracking_tab_active
        if callback:
            callback(self.view.notebook.select() == str(self.view.main_tab))

    def request_close(self):
        current_tab = self.view.notebook.select()
        if (
            current_tab == str(self.view.settings_tab)
            and self.context.panels.settings.is_dirty()
            and not self._confirm_leave()
        ):
            return
        self.context.callbacks.on_close()

    def _confirm_leave(self):
        choice = UnappliedChangesDialog(self.view.root).show()
        if choice == "cancel":
            return False
        if choice == "apply":
            self.context.panels.settings.apply()
        else:
            self.context.panels.settings.discard()
        return True
