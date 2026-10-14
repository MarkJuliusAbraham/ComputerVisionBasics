"""Fixed window sizing and initial placement shared by application windows."""


class WindowGeometry:
    def __init__(self, window, base_size, *, minimum_size=(320, 320)):
        self.window = window
        self.base_size = base_size
        self.minimum_size = minimum_size
        self.size = None
        # Tk removes the Windows resize border and maximize action together.
        # Apply this once; changing window styles during activation or dragging
        # can recreate the native wrapper and interrupt a move.
        self.window.resizable(False, False)

    def resize(self, scale):
        """Change size for an explicit UI scale change, retaining position."""
        width = min(round(self.base_size[0] * scale), self.window.winfo_screenwidth() - 48)
        height = min(round(self.base_size[1] * scale), self.window.winfo_screenheight() - 80)
        width = max(width, self.minimum_size[0])
        height = max(height, self.minimum_size[1])
        self.size = (width, height)
        self.window.geometry(f"{width}x{height}")

    # Space kept clear for the taskbar below placed windows.
    TASKBAR_MARGIN = 48

    def _move_on_screen(self, x, y, width, height):
        """Place the window at (x, y), clamped to the visible screen."""
        x = min(max(x, 0), max(0, self.window.winfo_screenwidth() - width))
        y = min(max(y, 0), max(0, self.window.winfo_screenheight() - height - self.TASKBAR_MARGIN))
        self.window.geometry(f"+{x}+{y}")

    def place_near(self, parent):
        """Set the initial position only, before the window is first shown."""
        self.window.update_idletasks()
        width, height = self.size or (self.window.winfo_width(), self.window.winfo_height())
        self._move_on_screen(parent.winfo_rootx() + 32, parent.winfo_rooty() + 32, width, height)

    def center_over(self, parent, *, requested=False):
        """Center once at opening, clamping placement to the visible screen."""
        self.window.update_idletasks()
        width, height = (
            (self.window.winfo_reqwidth(), self.window.winfo_reqheight()) if requested else
            self.size or (self.window.winfo_width(), self.window.winfo_height())
        )
        self._move_on_screen(
            parent.winfo_rootx() + (parent.winfo_width() - width) // 2,
            parent.winfo_rooty() + (parent.winfo_height() - height) // 2,
            width, height,
        )
