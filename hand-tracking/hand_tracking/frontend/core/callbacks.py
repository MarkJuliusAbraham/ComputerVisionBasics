"""Typed callback contracts shared by windows and replaceable panels."""

from collections.abc import Callable
from typing import TypeAlias

from hand_tracking.backend.settings.settings_manager import SettingsData, SettingsValues


Action: TypeAlias = Callable[[], None]
SettingsPathCallback: TypeAlias = Callable[[str], bool | None]
ApplySettingsCallback: TypeAlias = Callable[[SettingsValues], SettingsData | bool | None]
