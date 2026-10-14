"""A crisp, scaled inset-square indicator for themed ttk checkboxes."""

import tkinter as tk
from tkinter import ttk

from gui_tkinter.core.widget_tree import root_service

from .scaling import scale_pixels


class SquareCheckboxIndicator:
    ELEMENT_NAME = "Checkbutton.indicator"
    BASE_BORDER_WIDTH = 1
    BASE_MARKER_INSET = 2
    BASE_MIXED_HEIGHT = 2

    def __init__(self, root, theme_name, *, image_factory=None):
        self.root = root
        self.theme_name = theme_name
        self.image_factory = image_factory if image_factory is not None else tk.PhotoImage
        self._images = {}
        self._installed = False
        self._snapshot = None

    @classmethod
    def for_theme(cls, root, theme_name):
        # ttk stores image names, not Python references. Keep their owners on
        # the interpreter root so indicators survive theme switches and GC.
        providers = root_service(root, "_square_checkbox_indicators", lambda _root: {})
        if theme_name not in providers:
            providers[theme_name] = cls(root, theme_name)
        return providers[theme_name]

    def apply(self, palette, *, size, margins, scale):
        snapshot = (palette, size, margins, scale)
        if snapshot != self._snapshot:
            left, top, right, bottom = margins
            width, height = size + left + right, size + top + bottom
            for state in ("rest", "active", "disabled"):
                for marker in ("off", "on", "mixed"):
                    key = (state, marker)
                    image = self._images.get(key)
                    if image is None:
                        image = self.image_factory(master=self.root, width=width, height=height)
                        self._images[key] = image
                    else:
                        # Resize and redraw in place. The theme's image element
                        # keeps these names when the UI scale changes again.
                        image.configure(width=width, height=height)
                    self._draw(image, palette, size, left, top, scale, state, marker)
            self._snapshot = snapshot

        if not self._installed:
            images = self._images
            ttk.Style(self.root).theme_settings(self.theme_name, {
                self.ELEMENT_NAME: {
                    "element create": (
                        "image", images[("rest", "off")],
                        ("disabled", "alternate", images[("disabled", "mixed")]),
                        ("disabled", "selected", images[("disabled", "on")]),
                        ("disabled", images[("disabled", "off")]),
                        ("pressed", "alternate", images[("active", "mixed")]),
                        ("active", "alternate", images[("active", "mixed")]),
                        ("alternate", images[("rest", "mixed")]),
                        ("pressed", "selected", images[("active", "on")]),
                        ("active", "selected", images[("active", "on")]),
                        ("selected", images[("rest", "on")]),
                        ("pressed", images[("active", "off")]),
                        ("active", images[("active", "off")]),
                        {"sticky": "w"},
                    ),
                },
            })
            self._installed = True

    def _draw(self, image, palette, size, left, top, scale, state, marker):
        disabled = state == "disabled"
        face = palette.surface if disabled else (
            palette.hover if state == "active" else palette.field
        )
        upper = palette.border if disabled else palette.button_edges.shadow
        lower = palette.border if disabled else palette.button_edges.highlight
        ink = palette.disabled if disabled else palette.foreground
        stroke = scale_pixels(self.BASE_BORDER_WIDTH, scale, minimum=1)
        right, bottom = left + size, top + size
        image.blank()
        image.put(face, to=(left, top, right, bottom))
        image.put(upper, to=(left, top, right, top + stroke))
        image.put(upper, to=(left, top, left + stroke, bottom))
        image.put(lower, to=(left, bottom - stroke, right, bottom))
        image.put(lower, to=(right - stroke, top, right, bottom))
        inset = scale_pixels(self.BASE_MARKER_INSET, scale, minimum=stroke + 1)
        if marker == "on":
            image.put(ink, to=(left + inset, top + inset, right - inset, bottom - inset))
        elif marker == "mixed":
            height = scale_pixels(self.BASE_MIXED_HEIGHT, scale, minimum=1)
            y = top + (size - height) // 2
            image.put(ink, to=(left + inset, y, right - inset, y + height))
