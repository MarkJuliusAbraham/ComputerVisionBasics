"""Mapping labels for the shared commit/discard action component."""

from hand_tracking.ui.components.commit_actions import CommitActions


class MappingFooter(CommitActions):
    def __init__(self, master, appearance, on_save=None, on_discard=None):
        super().__init__(
            master, on_save=on_save, on_discard=on_discard,
            save_label="Save mappings", appearance=appearance,
        )
        self.set_status("Gesture mappings loaded")
