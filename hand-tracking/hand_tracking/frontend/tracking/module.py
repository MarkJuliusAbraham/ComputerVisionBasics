"""The small UI contract implemented by each tracking workspace."""

from typing import Protocol
import tkinter as tk


class TrackingModule(Protocol):
    key: str
    name: str
    description: str

    def open(self, parent: tk.Misc) -> None: ...

    def confirm_close(self) -> bool: ...

    def resize(self, scale: float) -> None: ...

    def close(self) -> None: ...
