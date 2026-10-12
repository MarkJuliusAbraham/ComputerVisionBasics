"""A theme-aware scrollable ttk container."""

import tkinter as tk
from tkinter import ttk


class ScrollableFrame(ttk.Frame):
    """Host a ttk form in a canvas without exposing canvas plumbing to callers."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._toplevel = self.winfo_toplevel()

        self.scrollbar = ttk.Scrollbar(self, orient="vertical")
        self.scrollbar.pack(side="right", fill="y")

        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.configure(command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.content = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window(
            (0, 0), window=self.content, anchor="nw"
        )
        self.content.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_content)
        self._toplevel.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind("<<ThemeChanged>>", lambda _event: self.set_surface())
        self.set_surface()

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_content(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)

    def set_surface(self):
        """Match the canvas background to the current ttk frame surface."""
        background = ttk.Style(self._toplevel).lookup("TFrame", "background")
        if not background:
            background = self._toplevel.cget("background")
        if background:
            self.canvas.configure(background=background)

    def _contains_widget(self, widget):
        current = widget
        while current is not None:
            if current == self.content:
                return True
            parent_path = current.winfo_parent()
            if not parent_path:
                return False
            try:
                current = self._toplevel.nametowidget(parent_path)
            except KeyError:
                return False
        return False

    def _on_mousewheel(self, event):
        if not self._contains_widget(event.widget) or not event.delta:
            return
        amount = -int(event.delta / 120) or (-1 if event.delta > 0 else 1)
        self.canvas.yview_scroll(amount, "units")
        return "break"

    def scroll_to(self, widget):
        """Scroll until ``widget`` is near the top of the visible form."""
        self.content.update_idletasks()
        total_height = self.content.winfo_height()
        if total_height:
            self.canvas.yview_moveto(widget.winfo_y() / total_height)
