"""Settings persistence shared by the hub and individual tracking modules."""

from copy import deepcopy
from tkinter import ttk

from settings.settings_manager import SHARED_SETTINGS_SCOPE, SettingsData
from gui_tkinter.components.buttons import DiscardChangesButton

from .settings_form import SettingsForm


class SettingsPanel:
    """Commit only the supplied scope and delegate controls to a supplied form."""

    def __init__(
        self, on_settings_path=None, on_apply=None, *,
        scope=SHARED_SETTINGS_SCOPE, form_factory=SettingsForm,
    ):
        self.on_settings_path = on_settings_path
        self.on_apply = on_apply
        self.scope = scope
        self.form_factory = form_factory
        self._baseline = SettingsData()
        self.form = None

    def build(self, parent, settings):
        self.root = parent.winfo_toplevel()
        content = ttk.Frame(parent)
        content.pack(fill="both", expand=True)
        footer = ttk.Frame(content)
        footer.pack(side="bottom", fill="x", padx=12, pady=12)
        self.apply_button = ttk.Button(
            footer, text="Apply", command=self.apply, style="Accent.TButton",
        )
        self.apply_button.pack(side="right")
        self.discard_button = DiscardChangesButton(footer, command=self.discard)
        self.discard_button.pack(side="right", padx=(0, 8))
        self.form = self.form_factory(
            content, settings=settings, on_change=self._refresh_apply_state,
            on_settings_path=self.on_settings_path,
        )
        ttk.Label(footer, textvariable=self.form.status_var, wraplength=360).pack(
            side="left", fill="x", expand=True,
        )
        ttk.Label(content, textvariable=self.form.validation_error, wraplength=600).pack(
            side="bottom", fill="x", padx=12,
        )
        self.form.pack(fill="both", expand=True, padx=12, pady=(12, 0))
        self.show_settings(settings)
        return self.form

    def get_values(self):
        return self.scope.merge(self._baseline, self.form.values())

    def is_dirty(self):
        return (
            self.form is not None
            and self.scope.values(self.get_values()) != self.scope.values(self._baseline)
        )

    def _refresh_apply_state(self):
        if self.form is None:
            return
        state = ["!disabled" if self.is_dirty() else "disabled"]
        self.apply_button.state(state)
        self.discard_button.state(state)

    def show_settings(self, settings):
        self._baseline = deepcopy(settings.data)
        if self.form is not None:
            self.form.load(settings)
            self.form.status_var.set(f"{self.scope.name} settings loaded")
            self._refresh_apply_state()

    def rebase(self, settings, changed_fields):
        """Refresh applied values without destroying another panel's draft."""
        if set(changed_fields).intersection(self.scope.fields):
            self.show_settings(settings)
        else:
            self._baseline = deepcopy(settings.data)
            self.set_theme(settings.data.theme)
            self._refresh_apply_state()

    def apply(self):
        data = self.get_values()
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
        self._baseline = deepcopy(result if isinstance(result, SettingsData) else data)
        self._refresh_apply_state()
        self.form.status_var.set(f"{self.scope.name} settings applied and saved")
        return True

    def discard(self):
        if self.form is not None:
            self.form.load_data(self._baseline)
            self.form.status_var.set("Unsaved settings discarded")
            self._refresh_apply_state()

    def set_theme(self, theme_name):
        if self.form is not None:
            self.form.set_theme(theme_name)
