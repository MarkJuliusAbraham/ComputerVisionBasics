"""Distinct surfaces and outlines for native dropdown lists and context menus."""

import tkinter as tk
from tkinter import ttk

from hand_tracking.frontend.core.widget_tree import root_service, walk_widgets


class PopupTheme:
    def __init__(self, root):
        self.root = root
        self.palette = None
        self.font_name = None
        # Combobox listboxes are created by Tcl, so they do not have Python
        # widget objects. Pass their paths directly without resolving %W.
        listbox_callback = root.register(self._style_listbox)
        menu_callback = root.register(self._style_menu)
        # For Tcl scripts Tkinter ignores its add argument. Prefix the script
        # with '+' so native focus, selection, and menu bindings stay intact.
        root.bind_class("ComboboxListbox", "<Map>", f"+{listbox_callback} %W")
        root.bind_class("Menu", "<Map>", f"+{menu_callback} %W")
        root.bind_class("Menu", "<<ThemeChanged>>", f"+{menu_callback} %W")

    @classmethod
    def for_root(cls, root):
        return root_service(root, "_popup_theme", cls)

    def apply(self, palette, font_name):
        self.palette = palette
        self.font_name = font_name
        ttk.Style(self.root).configure(
            "ComboboxPopdownFrame", background=palette.popup.surface,
            bordercolor=palette.popup.border, relief="solid", borderwidth=1,
        )
        # Defaults cover future popups; refreshes cover cached ones and menus
        # that were already created before a theme or scale change.
        for name, value in self._listbox_options().items():
            self.root.option_add(f"*TCombobox*Listbox.{name}", value)
        for name, value in self._menu_options().items():
            self.root.option_add(f"*Menu.{name}", value)
        self._update_existing()

    def _listbox_options(self):
        p = self.palette
        return {
            "background": p.popup.surface, "foreground": p.foreground,
            "selectBackground": p.selection, "selectForeground": p.selection_text,
            "highlightBackground": p.popup.border, "highlightColor": p.popup.border,
            "highlightThickness": 1, "borderWidth": 0, "relief": "flat",
            "selectBorderWidth": 0, "font": self.font_name,
        }

    def _menu_options(self):
        p = self.palette
        return {
            "background": p.popup.surface, "foreground": p.foreground,
            "activeBackground": p.selection, "activeForeground": p.selection_text,
            "disabledForeground": p.disabled, "activeBorderWidth": 0,
            "borderWidth": 1, "relief": "solid", "font": self.font_name,
        }

    def _update_existing(self):
        for widget in walk_widgets(self.root, include_parent=False):
            if isinstance(widget, ttk.Combobox):
                self._style_listbox(f"{widget}.popdown.f.l")
            elif isinstance(widget, tk.Menu):
                self._style_menu(str(widget))

    def _style_listbox(self, path):
        self._configure(path, self._listbox_options())

    def _style_menu(self, path):
        self._configure(path, self._menu_options())

    def _configure(self, path, options):
        try:
            if self.root.tk.call("winfo", "exists", path):
                args = tuple(
                    arg for name, value in options.items()
                    for arg in (f"-{name.lower()}", value)
                )
                self.root.tk.call(path, "configure", *args)
        except tk.TclError:
            # A cached popup may be destroyed while a theme event is queued.
            pass
