"""Variable subscriptions and nested-safe suppression of draft notifications."""

from contextlib import contextmanager
import tkinter as tk


class ChangeNotifications:
    def __init__(self, owner, on_change=None):
        self.on_change = on_change
        self._depth = 0
        self._subscriptions = []
        owner.bind("<Destroy>", self._destroyed, add="+")
        self.owner = owner

    def watch(self, *variables, callback=None):
        """Subscribe once; an optional callback translates a field interaction."""
        action = callback if callback is not None else self.on_change
        for variable in variables:
            if any(watched is variable for watched, _trace in self._subscriptions):
                continue
            trace = variable.trace_add("write", lambda *_args, action=action: self.emit(action))
            self._subscriptions.append((variable, trace))

    def emit(self, callback=None):
        action = callback if callback is not None else self.on_change
        if not self._depth and action is not None:
            action()

    @contextmanager
    def suspended(self):
        self._depth += 1
        try:
            yield
        finally:
            self._depth -= 1

    def _destroyed(self, event):
        if event.widget is not self.owner:
            return
        for variable, trace in self._subscriptions:
            try:
                variable.trace_remove("write", trace)
            except tk.TclError:
                pass  # The interpreter may already be shutting down.
        self._subscriptions.clear()
