"""Typed callback contracts shared by windows and replaceable panels."""

from collections.abc import Callable
from types import TracebackType
from typing import TypeAlias

from settings.settings_manager import SettingsData, SettingsValues


Action: TypeAlias = Callable[[], None]
SettingsPathCallback: TypeAlias = Callable[[str], bool | None]
ApplySettingsCallback: TypeAlias = Callable[[SettingsValues], SettingsData | bool | None]
ExceptionReporter: TypeAlias = Callable[
    [type[BaseException], BaseException, TracebackType | None], None,
]
