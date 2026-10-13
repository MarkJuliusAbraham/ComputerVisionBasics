"""Settings persistence shared by the hub and individual tracking modules."""

import tkinter as tk
from collections.abc import Iterable
from tkinter import ttk

from settings.settings_manager import SHARED_SETTINGS_SCOPE, Settings, SettingsData, SettingsScope
from gui_tkinter.components.commit_actions import CommitActions
from gui_tkinter.core.callbacks import ApplySettingsCallback, SettingsPathCallback

from .settings_form import SettingsForm
from .settings_session import SettingsSession


class SettingsPanel:
    """Commit only the supplied scope and delegate controls to a supplied form."""

    def __init__(
        self, on_settings_path: SettingsPathCallback | None = None,
        on_apply: ApplySettingsCallback | None = None, *,
        scope: SettingsScope = SHARED_SETTINGS_SCOPE, form_factory=SettingsForm,
    ):
        self.on_settings_path = on_settings_path
        self.on_apply = on_apply
        self.scope = scope
        self.form_factory = form_factory
        self.session = SettingsSession(scope)
        self.form = None

    def build(self, parent: tk.Misc, settings: Settings):
        self.root = parent.winfo_toplevel()
        content = ttk.Frame(parent)
        content.pack(fill="both", expand=True)
        footer = self.actions = CommitActions(
            content, on_save=self.apply, on_discard=self.discard, save_label="Apply",
        )
        footer.pack(side="bottom", fill="x", padx=12, pady=12)
        self.form = self.form_factory(
            content, settings=settings, on_change=self._refresh_apply_state,
            on_settings_path=self.on_settings_path,
        )
        footer.message.use_variable(self.form.status_var)
        ttk.Label(content, textvariable=self.form.validation_error, wraplength=600).pack(
            side="bottom", fill="x", padx=12,
        )
        self.form.pack(fill="both", expand=True, padx=12, pady=(12, 0))
        self.show_settings(settings)
        return self.form

    def get_values(self):
        return self.session.merge(self.form.values())

    def is_dirty(self) -> bool:
        return (
            self.form is not None
            and self.session.is_dirty(self.form.draft_values())
        )

    def _refresh_apply_state(self):
        if self.form is None:
            return
        self.actions.set_dirty(self.is_dirty())

    def show_settings(self, settings: Settings) -> None:
        self.session.rebase(settings.data)
        if self.form is not None:
            self.form.load(settings)
            self.session.accept(settings.data, self.form.draft_values())
            self.form.status_var.set(f"{self.scope.name} settings loaded")
            self._refresh_apply_state()

    def rebase(self, settings: Settings, changed_fields: Iterable[str]) -> None:
        """Refresh applied values without destroying another panel's draft."""
        if set(changed_fields).intersection(self.scope.fields):
            self.show_settings(settings)
        else:
            self.session.rebase(settings.data)
            self.set_theme(settings.data.theme)
            self._refresh_apply_state()

    def apply(self) -> bool:
        try:
            data = self.get_values()
        except ValueError as error:
            self.form.validation_error.set(str(error))
            return False
        error = self.scope.validation_error(data)
        self.form.validation_error.set(error)
        if error:
            return False
        try:
            result = self.on_apply(self.scope.values(data)) if self.on_apply else data
        except (OSError, ValueError) as error:
            self.form.status_var.set(f"Could not save settings: {error}")
            return False
        if result is False:
            return False
        self.session.accept(
            result if isinstance(result, SettingsData) else data, self.form.draft_values(),
        )
        self._refresh_apply_state()
        self.form.status_var.set(f"{self.scope.name} settings applied and saved")
        return True

    def discard(self) -> None:
        if self.form is not None:
            self.form.load_data(self.session.baseline)
            self.session.accept(self.session.baseline, self.form.draft_values())
            self.form.status_var.set("Unsaved settings discarded")
            self._refresh_apply_state()

    def set_theme(self, theme_name: str) -> None:
        if self.form is not None:
            self.form.set_theme(theme_name)
