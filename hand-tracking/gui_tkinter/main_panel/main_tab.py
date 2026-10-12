"""The application hub: shared camera and registered tracking workspaces."""

from tkinter import ttk

from gui_tkinter.components.camera_section import CameraSection
from gui_tkinter.components.scrollable_frame import ScrollableFrame
from gui_tkinter.components.theme import ThemeMetrics


class MainTab(ttk.Frame):
    def __init__(self, master, tracking_modules, callbacks, camera_index=0):
        super().__init__(master, padding=20)
        self.appearance = ThemeMetrics(self)
        actions = ttk.Frame(self)
        actions.pack(side="bottom", fill="x", pady=(16, 0))
        ttk.Button(actions, text="Exit", command=callbacks.on_close).pack(side="right")
        ttk.Button(actions, text="Restart", command=callbacks.on_restart).pack(
            side="right", padx=(0, 8),
        )
        scroll = ScrollableFrame(self)
        scroll.pack(fill="both", expand=True)
        ttk.Label(scroll.content, text="Tracking hub", font=self.appearance.heading_font).pack(
            anchor="w", pady=(0, 6),
        )
        ttk.Label(
            scroll.content, text="Open a tracking workspace to inspect data and configure its behavior.",
            wraplength=600,
        ).pack(anchor="w", pady=(0, 20))
        self.camera = CameraSection(
            scroll.content, camera_index=camera_index, on_switch=callbacks.on_camera_switch,
        )
        self.camera.pack(fill="x", pady=(0, 20))
        group = ttk.LabelFrame(scroll.content, text="Tracking workspaces", padding=16)
        group.pack(fill="x")
        for module in tracking_modules.modules.values():
            row = ttk.Frame(group)
            row.pack(fill="x", pady=8)
            row.columnconfigure(0, weight=1)
            ttk.Label(row, text=module.name, font=self.appearance.heading_font).grid(
                row=0, column=0, sticky="w",
            )
            ttk.Label(row, text=module.description, wraplength=500).grid(
                row=1, column=0, sticky="w", pady=(6, 0), padx=(0, 20),
            )
            ttk.Button(
                row, text="Open", command=lambda key=module.key: tracking_modules.open(key),
            ).grid(row=0, column=1, rowspan=2, sticky="e")
        self.bind("<<ThemeChanged>>", lambda _event: self.appearance.refresh())
