"""Shared save/discard decisions for editable panels before leaving them."""

from dataclasses import dataclass
from typing import Any, Callable

from gui_tkinter.components.unapplied_changes_dialog import UnappliedChangesDialog


@dataclass(frozen=True)
class PendingChanges:
    """A panel's draft and commit actions, independent of its implementation."""

    name: str
    is_dirty: Callable[[], bool]
    save: Callable[[], Any]
    discard: Callable[[], Any]


class UnsavedChangesGuard:
    def __init__(self, parent, *, dialog_factory=UnappliedChangesDialog):
        self.parent = parent
        self.dialog_factory = dialog_factory
        self._confirming = False

    def confirm(self, changes, *, return_label="Return"):
        if self._confirming:
            return False
        self._confirming = True
        try:
            if not changes.is_dirty():
                return True
            choice = self.dialog_factory(
                self.parent, context=changes.name, action_label="Save",
                return_label=return_label,
            ).show()
            if choice == "discard":
                return changes.discard() is not False
            if choice == "save":
                return changes.save() is not False
            return False
        finally:
            self._confirming = False
