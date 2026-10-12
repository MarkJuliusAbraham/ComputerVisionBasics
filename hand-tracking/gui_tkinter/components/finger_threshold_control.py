import tkinter as tk
from tkinter import ttk

from .theme import gesture_bar_background, gesture_classification_color


class FingerThresholdControl(ttk.Frame):
    """A shared deviation scale with draggable finger-class boundaries."""

    MAX_VALUE = 120
    HANDLE_RADIUS = 6
    PADDING = 14

    def __init__(self, master, straight_var, curled_var, closed_var, on_change=None):
        super().__init__(master)
        self.variables = (straight_var, curled_var, closed_var)
        self.on_change = on_change
        self.theme_name = "Light"
        self._dragging = None
        self._canvas_bg = self._get_canvas_background()

        self.canvas = tk.Canvas(
            self, height=92, background=self._canvas_bg,
            highlightthickness=0, borderwidth=0,
        )
        self.canvas.pack(fill="x", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.redraw())
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", lambda _event: setattr(self, "_dragging", None))

        for variable in self.variables:
            variable.trace_add("write", lambda *_: self.redraw())

        self.redraw()

    def set_theme(self, theme_name):
        self.theme_name = theme_name
        self._canvas_bg = self._get_canvas_background()
        self.canvas.configure(background=self._canvas_bg)
        self.redraw()

    def _get_canvas_background(self):
        style = ttk.Style(self)
        background = style.lookup("TFrame", "background")
        if background:
            return background

        # Some Sun Valley theme states leave this lookup empty. Its palette
        # provides the current theme's surface color directly.
        suffix = "dark" if style.theme_use().endswith("dark") else "light"
        colors = f"::ttk::theme::sv_{suffix}::colors"
        try:
            background = self.tk.call("set", f"{colors}(-bg)")
            if background:
                return background
        except tk.TclError:
            pass
        return self.winfo_toplevel().cget("background")

    def _positions(self):
        width = max(self.canvas.winfo_width(), 220)
        left, right = self.PADDING, width - self.PADDING
        return left, right, [
            left + (right - left) * float(variable.get()) / self.MAX_VALUE
            for variable in self.variables
        ]

    def redraw(self):
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        left, right, markers = self._positions()
        center_y = 43
        boundaries = [left, *markers, right]
        colors = [
            gesture_classification_color(self.theme_name, name)
            for name in ("straight", "partial", "curled", "closed")
        ]
        for start, end, color in zip(boundaries, boundaries[1:], colors):
            self.canvas.create_rectangle(
                start, center_y - 5, end, center_y + 5,
                fill=color, outline="",
            )
        self.canvas.create_rectangle(
            left, center_y - 5, right, center_y + 5,
            outline=gesture_bar_background(self.theme_name), width=1,
        )

        foreground = ttk.Style(self).lookup("TLabel", "foreground")
        value_labels = [f"{float(variable.get()):g}°" for variable in self.variables]
        label_levels = []
        for index, (marker, text) in enumerate(zip(markers, value_labels)):
            half_width = len(text) * 3.5
            level = next(
                (
                    candidate for candidate, _y in enumerate((2, 14, 26))
                    if all(
                        candidate != prior_level
                        or abs(marker - markers[prior_index])
                        >= half_width + len(value_labels[prior_index]) * 3.5 + 4
                        for prior_index, prior_level in enumerate(label_levels)
                    )
                ),
                2,
            )
            label_levels.append(level)

        for index, (marker, variable) in enumerate(zip(markers, self.variables)):
            color = colors[index]
            self.canvas.create_line(
                marker, center_y - 12, marker, center_y + 12,
                fill=color, width=2,
            )
            self.canvas.create_oval(
                marker - self.HANDLE_RADIUS, center_y - self.HANDLE_RADIUS,
                marker + self.HANDLE_RADIUS, center_y + self.HANDLE_RADIUS,
                fill=color, outline=self._canvas_bg, width=1,
                tags=(f"handle-{index}",),
            )
            self.canvas.create_text(
                marker, (2, 14, 26)[label_levels[index]],
                text=value_labels[index], fill=foreground, anchor="n",
            )

        labels = ("Straight", "Partial", "Curled", "Closed")
        for start, end, label, color in zip(
            boundaries, boundaries[1:], labels, colors
        ):
            segment_width = end - start
            required_width = len(label) * 6 + 6
            if segment_width >= required_width:
                self.canvas.create_text(
                    (start + end) / 2, 80, text=label, fill=color, anchor="center",
                    font=("TkDefaultFont", 8),
                )

    def _start_drag(self, event):
        _left, _right, markers = self._positions()
        if markers:
            self._dragging = min(range(3), key=lambda index: abs(markers[index] - event.x))
            self._drag(event)

    def _drag(self, event):
        if self._dragging is None:
            return
        left, right, _markers = self._positions()
        position = min(max(event.x, left), right)
        value = round((position - left) / (right - left) * self.MAX_VALUE)
        index = self._dragging
        lower = int(float(self.variables[index - 1].get())) + 1 if index else 0
        upper = int(float(self.variables[index + 1].get())) - 1 if index < 2 else self.MAX_VALUE
        self.variables[index].set(min(max(value, lower), upper))
        if self.on_change:
            self.on_change()

