"""Window registration and coordination without tracker-specific UI logic."""

from collections.abc import Iterable

from .module import TrackingModule


class TrackingWindowRegistry:
    def __init__(self, modules: Iterable[TrackingModule]):
        self.modules = {module.key: module for module in modules}
        self.parent = None

    def attach(self, parent):
        self.parent = parent

    def open(self, key):
        self.modules[key].open(self.parent)

    def confirm_close(self):
        return all(module.confirm_close() for module in self.modules.values())

    def resize(self, scale):
        for module in self.modules.values():
            module.resize(scale)

    def close(self):
        for module in self.modules.values():
            module.close()
