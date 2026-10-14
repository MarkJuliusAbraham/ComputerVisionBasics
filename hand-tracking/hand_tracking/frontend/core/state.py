"""Small reusable state and dependency containers for the Tkinter UI."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk
from typing import TYPE_CHECKING, Callable, Generic, TypeVar

from hand_tracking.backend.settings.settings_manager import Settings
from hand_tracking.frontend.components.guarded_notebook import GuardedNotebook

from .callbacks import Action, ApplySettingsCallback, ExceptionReporter, SettingsPathCallback
from .panel_contracts import MainPanelContract, MappingPanelContract, PanelCollection, SettingsPanelContract

if TYPE_CHECKING:
    from hand_tracking.frontend.tracking.registry import TrackingWindowRegistry

MainPanelType = TypeVar("MainPanelType", bound=MainPanelContract)


@dataclass
class CameraState:
    """Capture selection state shared by camera-facing UI components."""

    requested_index: int = 0
    active_index: int | None = None
    is_active: bool = False
    is_switching: bool = True

    def begin_switch(self, index: int) -> None:
        self.requested_index = index
        self.is_switching = True

    def mark_ready(self, index: int) -> None:
        self.requested_index = index
        self.active_index = index
        self.is_active = True
        self.is_switching = False

    def mark_failed(self, active_index: int | None = None) -> None:
        self.active_index = active_index
        self.is_active = False
        self.is_switching = False


@dataclass
class ControlCallbacks:
    """Application callbacks consumed by the control surface."""

    on_restart: Action
    on_close: Action
    on_settings_path: SettingsPathCallback | None = None
    on_apply: ApplySettingsCallback | None = None
    on_camera_switch: Callable[[int], None] | None = None
    on_toggle_tracking: Action | None = None
    on_main_active: Callable[[bool], None] | None = None


@dataclass
class PanelSet(Generic[MainPanelType]):
    """Replaceable panels hosted by either the hub or a tracking window."""

    main: MainPanelType
    settings: SettingsPanelContract
    mapping: MappingPanelContract | None = None


@dataclass
class WindowContext:
    """Dependencies shared by the hub shell and individual tracking windows."""

    settings: Settings
    callbacks: ControlCallbacks
    panels: PanelCollection
    camera_index: int = 0


@dataclass
class ControlWindowContext(WindowContext):
    """Hub dependencies, including its required tracking-window registry."""

    tracking_modules: TrackingWindowRegistry = field(kw_only=True)


@dataclass
class WindowView:
    """Tk widgets and selection state owned by the window shell."""

    root: tk.Tk | tk.Toplevel
    notebook: GuardedNotebook
    main_tab: ttk.Frame
    settings_tab: ttk.Frame
    mapping_tab: ttk.Frame | None = None
    current_tab: str | None = None
    default_callback_exception: ExceptionReporter | None = None
