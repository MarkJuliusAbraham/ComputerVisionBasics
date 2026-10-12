"""Shared finger row structure for both criteria editing tables."""

from tkinter import ttk

from ..criteria_options import FINGER_NAMES


class FingerCriteriaTable(ttk.Frame):
    """Align row labels and dividers without forcing data columns wider."""

    def __init__(self, master, appearance):
        super().__init__(master)
        self.appearance = appearance
        self._metrics = None
        self._label_width = None
        self._column_count = None
        self.heading("Finger", 0)
        divider = ttk.Separator(self, orient="horizontal")
        divider.grid(row=1, column=0, sticky="ew")
        self._dividers = [divider]
        for index, name in enumerate(FINGER_NAMES):
            row = self.finger_row(index)
            ttk.Label(self, text=name.title(), anchor="w", width=1).grid(
                row=row, column=0, sticky="ew",
            )
            if index + 1 < len(FINGER_NAMES):
                divider = ttk.Separator(self, orient="horizontal")
                divider.grid(row=row + 1, column=0, sticky="ew")
                self._dividers.append(divider)
        self.bind("<Configure>", self._resized)

    @staticmethod
    def finger_row(index):
        return 2 * index + 2

    def heading(self, text, column, center=False):
        label = ttk.Label(
            self, text=text, font=self.appearance.heading_font, width=1,
            anchor="center" if center else "w", justify="center" if center else "left",
        )
        label.grid(row=0, column=column, sticky="ew")
        return label

    def set_column_count(self, count):
        if count != self._column_count:
            for divider in self._dividers:
                divider.grid_configure(columnspan=count)
            self._column_count = count

    def apply_metrics(self, metrics):
        self._metrics = metrics
        self.rowconfigure(0, minsize=metrics.heading_height)
        for index in range(len(FINGER_NAMES)):
            self.rowconfigure(
                self.finger_row(index), minsize=metrics.row_height, uniform="finger",
            )
            self.rowconfigure(2 * index + 1, minsize=metrics.divider_height)
        self._size_label_column()

    def _resized(self, _event):
        self._size_label_column()

    def _size_label_column(self):
        if self._metrics is None:
            return
        width = self.winfo_width()
        label_width = self._metrics.label_width
        if width > 1:
            label_width = min(label_width, width // 3)
        if label_width != self._label_width:
            self.columnconfigure(0, minsize=label_width, weight=0)
            self._label_width = label_width
