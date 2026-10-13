"""Window registration and coordination without tracker-specific UI logic."""

from collections.abc import Iterable
import tkinter as tk

from .module import TrackingModule


class TrackingWindowRegistry:
    def __init__(self, modules: Iterable[TrackingModule]) -> None:
        self.modules = {module.key: module for module in modules}
        self.parent: tk.Misc | None = None

    def attach(self, parent: tk.Misc) -> None:
        self.parent = parent

    def open(self, key: str) -> None:
        if self.parent is None:
            raise RuntimeError("Attach the tracking registry to its parent window before opening a workspace")
        self.modules[key].open(self.parent)

    def confirm_close(self) -> bool:
        return all(module.confirm_close() for module in self.modules.values())

    def resize(self, scale: float) -> None:
        for module in self.modules.values():
            module.resize(scale)

    def close(self) -> None:
        for module in self.modules.values():
            module.close()
