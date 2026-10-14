"""Spacing declared once at 100% scale and re-applied when the theme changes."""

from .idle_refresh import IdleRefresh

SCALED_OPTIONS = frozenset({
    "padx", "pady", "ipadx", "ipady", "padding", "width", "height", "wraplength",
})


def _scale(value, pixels):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return pixels(value)
    if isinstance(value, tuple):
        return tuple(_scale(item, pixels) for item in value)
    return value


class ScaledLayout:
    """Remember widgets' geometry options in base pixels and rescale them.

    Owners declare a widget's placement and spacing once with ``pack``,
    ``grid``, or ``configure``. When the theme or UI scale changes, the same
    declarations are applied again at the new scale, so the spacing is not
    written a second time in a refresh method. Widgets hidden with
    ``pack_forget`` keep their declaration and return with ``show``.
    """

    def __init__(self, owner, appearance, *, on_refresh=None):
        self.appearance = appearance
        self._on_refresh = on_refresh
        self._entries = {}
        self.refresh_request = IdleRefresh(owner, self.refresh, event="<<ThemeChanged>>")

    def _scaled(self, options, *, spacing_only=False):
        return {
            name: _scale(value, self.appearance.pixels) if name in SCALED_OPTIONS else value
            for name, value in options.items()
            if not spacing_only or name in SCALED_OPTIONS
        }

    def _declare(self, widget, manager, options):
        self._entries[(str(widget), manager)] = (widget, manager, options)
        return self._scaled(options)

    def pack(self, widget, **options):
        widget.pack(**self._declare(widget, "pack", options))
        return widget

    def grid(self, widget, **options):
        widget.grid(**self._declare(widget, "grid", options))
        return widget

    def configure(self, widget, **options):
        widget.configure(**self._declare(widget, "configure", options))
        return widget

    def show(self, *widgets):
        """Re-pack widgets in the given order with their declared options."""
        for widget in widgets:
            _widget, _manager, options = self._entries[(str(widget), "pack")]
            widget.pack(**self._scaled(options))

    def refresh(self):
        self.appearance.refresh()
        for widget, manager, options in self._entries.values():
            scaled = self._scaled(options, spacing_only=True)
            if not scaled:
                continue
            if manager == "configure":
                widget.configure(**scaled)
            elif widget.winfo_manager() == manager:
                getattr(widget, f"{manager}_configure")(**scaled)
        if self._on_refresh is not None:
            self._on_refresh()
