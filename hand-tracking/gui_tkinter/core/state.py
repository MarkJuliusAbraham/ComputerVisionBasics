"""Small reusable state and dependency containers for the Tkinter UI."""

from dataclasses import dataclass
from typing import Any, Callable


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

    on_restart: Callable[[], Any]
    on_close: Callable[[], Any]
    on_settings_path: Callable[[str], Any] | None = None
    on_apply: Callable[[Any], Any] | None = None
    on_camera_switch: Callable[[int], Any] | None = None
    on_toggle_tracking: Callable[[], Any] | None = None
    on_main_active: Callable[[bool], Any] | None = None


@dataclass
class PanelSet:
    """Replaceable panels hosted by either the hub or a tracking window."""

    main: Any
    settings: Any
    mapping: Any | None = None


@dataclass
class ControlWindowContext:
    """All external dependencies required to construct a control window."""

    settings: Any
    callbacks: ControlCallbacks
    panels: PanelSet
    camera_index: int = 0
    tracking_modules: Any | None = None


@dataclass
class WindowView:
    """Tk widgets and selection state owned by the window shell."""

    root: Any
    notebook: Any
    main_tab: Any
    settings_tab: Any
    mapping_tab: Any | None = None
    current_tab: str | None = None
    default_callback_exception: Any | None = None
