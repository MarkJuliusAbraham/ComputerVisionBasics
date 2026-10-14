"""Applied settings and their raw form snapshot, without widget dependencies."""

from copy import deepcopy

from hand_tracking.settings.settings_manager import SettingsData


class SettingsSession:
    def __init__(self, scope):
        self.scope = scope
        self.baseline = SettingsData()
        self.form_baseline = {}

    def accept(self, data, draft_values):
        self.baseline = deepcopy(data)
        self.form_baseline = deepcopy(draft_values)

    def rebase(self, data):
        """Update other scopes' applied values while keeping this form's draft."""
        self.baseline = deepcopy(data)

    def is_dirty(self, draft_values):
        return draft_values != self.form_baseline

    def merge(self, values):
        return self.scope.merge(self.baseline, values)
