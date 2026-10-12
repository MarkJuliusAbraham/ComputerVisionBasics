"""Scoped entry point for hand tracking settings."""

from gui_tkinter.settings_panel import SettingsPanel
from settings.settings_manager import HAND_SETTINGS_SCOPE

from .settings_form import HandSettingsForm


class HandSettingsPanel(SettingsPanel):
    def __init__(self, on_apply=None):
        super().__init__(on_apply=on_apply, scope=HAND_SETTINGS_SCOPE, form_factory=HandSettingsForm)

    @property
    def tracking_preview_active(self):
        return self.form is not None and self.form.tracking_preview_active

    def set_preview_data(self, fingers, status):
        if self.form is not None:
            self.form.set_preview_data(fingers, status)
