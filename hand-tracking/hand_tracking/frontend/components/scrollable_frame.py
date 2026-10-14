"""A theme-aware scrollable ttk container."""

import tkinter as tk
from tkinter import ttk

from .scroll_viewport import ScrollViewport, ScrollWheelRouter


class ScrollableFrame(ttk.Frame):
    """Host a ttk form in a canvas without exposing canvas plumbing to callers."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._toplevel = self.winfo_toplevel()

        self.scrollbar = ttk.Scrollbar(self, orient="vertical")
        self.scrollbar.pack(side="right", fill="y")

        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.content = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window(
            (0, 0), window=self.content, anchor="nw"
        )
        self.viewport = ScrollViewport(self.canvas, self.content)
        self.scrollbar.configure(command=self.viewport.yview)
        self.content.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_content)
        ScrollWheelRouter.install(self._root(), self.for_event)
        self.bind("<<ThemeChanged>>", lambda _event: self.set_surface())
        self.set_surface()

    def _update_scroll_region(self, _event=None):
        self.viewport.refresh()

    def _resize_content(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)
        self.viewport.refresh()

    def set_surface(self):
        """Match the canvas background to the current ttk frame surface."""
        background = ttk.Style(self._toplevel).lookup("TFrame", "background")
        if not background:
            background = self._toplevel.cget("background")
        if background:
            self.canvas.configure(background=background)

    @classmethod
    def for_event(cls, event):
        """Find the nearest scroll container under the pointer, regardless of focus."""
        widget = event.widget
        if not isinstance(widget, tk.Misc):
            # Tk's native dropdown listbox is not a Python-managed widget.
            return None
        try:
            widget = widget.winfo_toplevel().winfo_containing(
                event.x_root, event.y_root,
            ) or widget
        except (KeyError, tk.TclError):
            return None
        while widget is not None:
            if isinstance(widget, cls):
                return widget
            widget = widget.master
        return None

    def scroll_mousewheel(self, event):
        """Scroll the page without invoking wheel bindings on its input fields."""
        button = getattr(event, "num", None)
        delta = getattr(event, "delta", 0)
        if button in (4, 5):
            amount = -1 if button == 4 else 1
        elif delta:
            amount = -int(delta / 120) or (-1 if delta > 0 else 1)
        else:
            return
        self.viewport.scroll_units(amount)
        return "break"

    def scroll_to(self, widget):
        """Scroll until ``widget`` is near the top of the visible form."""
        self.content.update_idletasks()
        self.viewport.scroll_to(widget)
