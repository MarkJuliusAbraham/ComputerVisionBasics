"""Settings that apply to the shared application hub."""

from .sectioned_form import SectionedSettingsForm
from .sections import AdvancedSection, AppearanceSection, DiagnosticsSection


class SettingsForm(SectionedSettingsForm):
    def __init__(self, master, *, settings, on_change=None, on_settings_path=None):
        super().__init__(master, on_change)
        self.add_section("Appearance", AppearanceSection(
            self.scroll.content, on_change=self.notify_change,
        ))
        self.add_section("Diagnostics", DiagnosticsSection(
            self.scroll.content, on_change=self.notify_change,
        ))
        self.advanced = AdvancedSection(self.scroll.content, on_path=on_settings_path)
        self.advanced.pack(fill="x")
        self.path_var = self.advanced.path
        self.status_var = self.advanced.status

    def load(self, settings):
        super().load(settings)
        self.advanced.load(settings.path)

    def browse(self):
        self.advanced.browse()
