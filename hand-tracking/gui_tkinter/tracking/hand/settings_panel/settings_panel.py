"""Scoped entry point for hand tracking settings."""

from functools import partial

from gui_tkinter.settings_panel import SettingsPanel
from settings.settings_manager import HAND_SETTINGS_SCOPE

from .settings_form import HandSettingsForm


class HandSettingsPanel(SettingsPanel):
    def __init__(self, on_apply=None, *, model_asset=None):
        super().__init__(
            on_apply=on_apply, scope=HAND_SETTINGS_SCOPE,
            form_factory=partial(HandSettingsForm, model_asset=model_asset),
        )
        self._model_status = None

    def build(self, parent, settings):
        form = super().build(parent, settings)
        if self._model_status is not None:
            form.model.set_model_status(self._model_status)
        return form

    def set_model_status(self, status):
        self._model_status = status
        if self.form is not None:
            self.form.model.set_model_status(status)

    @property
    def tracking_preview_active(self):
        return self.form is not None and self.form.tracking_preview_active

    def set_preview_data(self, fingers, status):
        if self.form is not None:
            self.form.set_preview_data(fingers, status)
