"""Keep canvas scrolling confined to the actual overflow of its content."""

from gui_tkinter.core.widget_tree import root_service

WHEEL_EVENTS = ("<MouseWheel>", "<Button-4>", "<Button-5>")


class ScrollWheelRouter:
    """One root-owned wheel binding that also survives closing child dialogs."""

    def __init__(self, root, resolve_container):
        self.resolve_container = resolve_container
        for event in WHEEL_EVENTS:
            root.bind_all(event, self._on_wheel, add="+")

    @classmethod
    def install(cls, root, resolve_container):
        return root_service(root, "_scroll_wheel_router", lambda owner: cls(owner, resolve_container))

    def _on_wheel(self, event):
        container = self.resolve_container(event)
        if container is not None:
            return container.scroll_mousewheel(event)


class ScrollViewport:
    def __init__(self, canvas, content):
        self.canvas = canvas
        self.content = content
        self._overflow = False

    def refresh(self):
        width = max(self.canvas.winfo_width(), 1)
        viewport_height = max(self.canvas.winfo_height(), 1)
        content_height = max(self.content.winfo_reqheight(), self.content.winfo_height())
        self._overflow = content_height > viewport_height
        self.canvas.configure(scrollregion=(0, 0, width, max(content_height, viewport_height)))
        if not self._overflow:
            self.canvas.yview_moveto(0)

    def yview(self, *args):
        if not self._overflow:
            self.canvas.yview_moveto(0)
            return
        self.canvas.yview(*args)

    def scroll_units(self, amount):
        first, last = self.canvas.yview()
        if self._overflow and not (
            amount < 0 and first <= 0 or amount > 0 and last >= 1
        ):
            self.canvas.yview_scroll(amount, "units")

    def scroll_to(self, widget):
        self.refresh()
        if self._overflow:
            self.canvas.yview_moveto(widget.winfo_y() / self.content.winfo_height())
