"""Actions supplied to a mapping view as one replaceable dependency."""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class MappingCallbacks:
    on_change: Callable[[], None] | None = None
    on_repeat_change: Callable[[], None] | None = None
    on_select: Callable[[str], None] | None = None
    on_manage: Callable[[], None] | None = None
    on_rename: Callable[[str], None] | None = None
    on_delete: Callable[[str], None] | None = None
    on_choose_profile: Callable[[], None] | None = None
    on_edit_reset: Callable[[], None] | None = None
    on_save: Callable[[], bool] | None = None
    on_discard: Callable[[], None] | None = None
