"""Shared save/discard decisions for editable panels before leaving them."""

from dataclasses import dataclass
from typing import Callable
import tkinter as tk

from hand_tracking.ui.components.unapplied_changes_dialog import UnappliedChangesDialog


@dataclass(frozen=True)
class PendingChanges:
    """A panel's draft and commit actions, independent of its implementation."""

    name: str
    is_dirty: Callable[[], bool]
    save: Callable[[], bool | None]
    discard: Callable[[], bool | None]


class UnsavedChangesGuard:
    def __init__(self, parent: tk.Misc, *, dialog_factory=UnappliedChangesDialog) -> None:
        self.parent = parent
        self.dialog_factory = dialog_factory
        self._confirming = False

    def confirm(self, changes: PendingChanges, *, return_label: str = "Return") -> bool:
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
