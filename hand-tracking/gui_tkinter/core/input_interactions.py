"""Consistent focus and mouse-wheel behavior for application inputs."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.components.scrollable_frame import ScrollableFrame
from gui_tkinter.components.scroll_viewport import WHEEL_EVENTS

from .widget_tree import walk_widgets


class InputInteractionController:
    """Clear focus on background clicks and protect field values from scrolling."""

    FIELD_CLASSES = ("TCombobox", "TSpinbox", "Spinbox")
    BACKGROUND_CLASSES = {
        "tk", "toplevel", "frame", "tframe", "labelframe", "tlabelframe",
        "label", "tlabel", "separator", "tseparator", "canvas",
    }

    def __init__(self, root):
        self.root = root
        self._wheel_tag = f"InputWheelGuard_{id(self)}"
        self._bound = False

    def bind(self):
        if self._bound:
            return
        self._bound = True
        self.root.bind_all("<Button-1>", self._background_clicked, add="+")
        for event in WHEEL_EVENTS:
            self.root.bind_class(self._wheel_tag, event, self._field_mousewheel)
        # Map bindings cover inputs in dialogs opened after the main window.
        for widget_class in self.FIELD_CLASSES:
            self.root.bind_class(widget_class, "<Map>", self._field_mapped, add="+")
        for widget in walk_widgets(self.root):
            self._register_field(widget)

    def _register_field(self, widget):
        if not isinstance(widget, tk.Misc) or widget.winfo_class() not in self.FIELD_CLASSES:
            return
        tags = widget.bindtags()
        if self._wheel_tag not in tags:
            # Run before widget/class bindings can cycle the selected value.
            widget.bindtags((self._wheel_tag, *tags))

    def _field_mapped(self, event):
        self._register_field(event.widget)

    def _background_clicked(self, event):
        widget = event.widget
        if (
            isinstance(widget, tk.Misc)
            and widget.winfo_class().lower() in self.BACKGROUND_CLASSES
        ):
            widget.winfo_toplevel().focus_set()

    def _field_mousewheel(self, event):
        # A posted dropdown list keeps its native scrolling behavior. Its
        # listbox does not receive our field tag; the closed input never cycles.
        if isinstance(event.widget, ttk.Combobox) and event.widget.instate(["pressed"]):
            return "break"
        container = ScrollableFrame.for_event(event)
        if container is not None:
            container.scroll_mousewheel(event)
        return "break"
