"""The interfaces the window shell requires from its replaceable panels."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Iterable
from tkinter import ttk
from typing import TYPE_CHECKING, Protocol

from hand_tracking.backend.settings.settings_manager import Settings, SettingsData

from .callbacks import ApplySettingsCallback, SettingsPathCallback

if TYPE_CHECKING:
    from .state import ControlCallbacks


class MainPanelContract(Protocol):
    def build(
        self, parent: tk.Misc, *, callbacks: ControlCallbacks,
        settings: SettingsData, camera_index: int = 0,
    ) -> ttk.Frame: ...


class SettingsPanelContract(Protocol):
    on_settings_path: SettingsPathCallback | None
    on_apply: ApplySettingsCallback | None

    def build(self, parent: tk.Misc, settings: Settings) -> ttk.Frame: ...
    def is_dirty(self) -> bool: ...
    def apply(self) -> bool: ...
    def discard(self) -> None: ...
    def show_settings(self, settings: Settings) -> None: ...
    def rebase(self, settings: Settings, changed_fields: Iterable[str]) -> None: ...
    def set_theme(self, theme_name: str) -> None: ...


class MappingPanelContract(Protocol):
    def build(self, parent: tk.Misc) -> ttk.Frame: ...
    def is_dirty(self) -> bool: ...
    def save(self) -> bool: ...
    def discard(self) -> None: ...


class PanelCollection(Protocol):
    """Read panels through their interfaces while preserving concrete owners."""

    @property
    def main(self) -> MainPanelContract: ...

    @property
    def settings(self) -> SettingsPanelContract: ...

    @property
    def mapping(self) -> MappingPanelContract | None: ...
