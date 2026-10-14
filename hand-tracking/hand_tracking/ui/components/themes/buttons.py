"""Visible, theme-managed button edges shared by all four themes."""

from tkinter import ttk


class ButtonTheme:
    BORDER_ELEMENT = "AppButton.border"

    def __init__(self, root, palette, *, minimum_width=None):
        self.root = root
        self.palette = palette
        self.minimum_width = minimum_width

    def apply(self):
        style = ttk.Style(self.root)
        p = self.palette
        edges = p.button_edges
        if self.BORDER_ELEMENT not in style.element_names():
            # Sun Valley's button images contain their own edge colors.
            # Use Tk's native bevel renderer so our palette controls the edge.
            style.element_create(self.BORDER_ELEMENT, "from", "clam", "border")
        layout = [(self.BORDER_ELEMENT, {
            "sticky": "nswe", "border": 1, "children": [("Button.focus", {
                "sticky": "nswe", "children": [("Button.padding", {
                    "sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})],
                })],
            })],
        })]
        for name in ("TButton", "Accent.TButton"):
            style.layout(name, layout)
        if self.minimum_width is not None:
            style.configure("TButton", width=self.minimum_width)

        style.configure(
            "TButton", background=p.panel, foreground=p.foreground,
            bordercolor=edges.outline, lightcolor=edges.highlight, darkcolor=edges.shadow,
            borderwidth=2, relief="raised", anchor="center", focuscolor=p.foreground,
        )
        style.map(
            "TButton",
            background=[("disabled", p.surface), ("pressed", p.hover), ("active", p.hover)],
            foreground=[("disabled", p.disabled), ("!disabled", p.foreground)],
            relief=[("disabled", "solid"), ("pressed", "sunken")],
            bordercolor=[("disabled", p.border), ("focus", p.foreground)],
            lightcolor=[("disabled", p.border), ("!disabled", edges.highlight)],
            darkcolor=[("disabled", p.border), ("!disabled", edges.shadow)],
        )
        # Primary actions already have a distinct fill; a solid edge keeps
        # them readable without reusing a neutral bevel on a colored face.
        style.configure(
            "Accent.TButton", background=p.selection, foreground=p.selection_text,
            bordercolor=edges.outline, relief="solid",
        )
        style.map(
            "Accent.TButton",
            background=[("disabled", p.surface), ("!disabled", p.selection)],
            foreground=[("disabled", p.disabled), ("!disabled", p.selection_text)],
            bordercolor=[("disabled", p.border), ("focus", p.foreground),
                         ("!disabled", edges.outline)],
            relief=[("disabled", "solid"), ("pressed", "sunken"), ("!disabled", "solid")],
        )
        # DestructiveButtonStyle owns the filled destructive-action palette;
        # it inherits this layout, typography, spacing, and border geometry.
