"""Coalesce widget refresh requests and cancel them when their owner closes."""

import tkinter as tk


class IdleRefresh:
    def __init__(self, owner, callback, *, event=None):
        self.owner = owner
        self.callback = callback
        self._pending = None
        self._closed = False
        owner.bind("<Destroy>", self._destroyed, add="+")
        if event is not None:
            owner.bind(event, self.schedule, add="+")

    def schedule(self, _event=None):
        if not self._closed and self._pending is None:
            self._pending = self.owner.after_idle(self._run)

    def _run(self):
        self._pending = None
        if not self._closed:
            self.callback()

    def _destroyed(self, event):
        if event.widget is not self.owner:
            return
        self._closed = True
        if self._pending is not None:
            try:
                self.owner.after_cancel(self._pending)
            except tk.TclError:
                pass
            self._pending = None
