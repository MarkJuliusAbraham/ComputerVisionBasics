import tkinter as tk
from tkinter import filedialog, ttk

from control_panel.theme import apply_theme, resolve_scale
from control_panel.unapplied_changes_dialog import UnappliedChangesDialog
from settings.settings_manager import Settings, SettingsData, THEMES, UI_SCALES

BASE_SIZE = (640, 600)  # window size in pixels at 100%

class ControlWindow:
    """Control panel with Main and Settings tabs."""

    def __init__(
        self,
        on_restart,
        on_close,
        settings,
        on_settings_path=None,
        on_apply=None,
        camera_index=0,
        on_camera_switch=None,
    ):
        self.on_settings_path = on_settings_path
        self.on_apply = on_apply
        self.on_camera_switch = on_camera_switch
        self.camera_index = camera_index
        self._camera_active = False
        self._camera_switching = True
        self._baseline = SettingsData()

        self.root = tk.Tk()
        self.root.title("Controls")
        self.root.resizable(False, False)
        self._scale = None  # last applied scale, set by _apply_display

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        main_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(main_tab, text="Main")
        self.notebook.add(self.settings_tab, text="Settings")
        settings_tab = self.settings_tab

        # Main tab
        actions = ttk.Frame(main_tab)
        actions.pack(fill="x", padx=20, pady=(14, 2))
        ttk.Button(actions, text="Restart", command=on_restart).pack(
            side="left", fill="x", expand=True, padx=(0, 5)
        )
        ttk.Button(actions, text="Exit", command=on_close).pack(
            side="left", fill="x", expand=True, padx=(5, 0)
        )

        camera_section = ttk.LabelFrame(
            main_tab, text="Camera", padding=(12, 8, 12, 10)
        )
        camera_section.pack(fill="x", padx=20, pady=(8, 8))
        camera_row = ttk.Frame(camera_section)
        camera_row.pack(fill="x")
        ttk.Label(camera_row, text="Device").pack(side="left")
        self.camera_var = tk.StringVar(value=str(camera_index))
        self.camera_picker = ttk.Combobox(
            camera_row, textvariable=self.camera_var,
            values=[str(index) for index in range(10)],
            state="readonly", width=8,
        )
        self.camera_picker.pack(side="left", padx=(8, 0))
        self.camera_switch_button = ttk.Button(
            camera_section, text="Switch", command=self.switch_camera,
            style="Accent.TButton",
        )
        self.camera_switch_button.pack(anchor="e", pady=(8, 0))
        self.camera_status = tk.StringVar(value="Current camera")
        ttk.Label(camera_section, textvariable=self.camera_status).pack(
            anchor="w", pady=(6, 0)
        )

        gesture_section = ttk.LabelFrame(
            main_tab, text="Live gesture data", padding=(10, 6, 10, 8)
        )
        gesture_section.pack(fill="both", expand=True, padx=20, pady=(2, 14))
        self.gesture_enabled = tk.StringVar(value="Waiting for camera…")
        ttk.Label(gesture_section, textvariable=self.gesture_enabled).pack(
            anchor="w", pady=(0, 5)
        )
        hands_row = ttk.Frame(gesture_section)
        hands_row.pack(fill="both", expand=True)
        self.gesture_display = {}
        for column, handedness in enumerate(("Left", "Right")):
            panel = ttk.LabelFrame(hands_row, text=f"{handedness} hand", padding=(6, 4))
            panel.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 5, 0))
            hands_row.columnconfigure(column, weight=1, uniform="hand")
            hands_row.rowconfigure(0, weight=1)

            values = {
                "palm": tk.StringVar(value="—"),
                "gesture": tk.StringVar(value="—"),
                "pinch": tk.StringVar(value="—"),
                "fingers": {},
            }
            ttk.Label(panel, text="Palm").grid(row=0, column=0, sticky="w")
            ttk.Label(panel, textvariable=values["palm"]).grid(row=0, column=1, sticky="w")
            ttk.Label(panel, text="Command").grid(row=1, column=0, sticky="w")
            ttk.Label(panel, textvariable=values["gesture"]).grid(row=1, column=1, sticky="w")
            ttk.Label(panel, text="Pinch").grid(row=2, column=0, sticky="nw")
            ttk.Label(
                panel, textvariable=values["pinch"], wraplength=220, justify="left"
            ).grid(row=2, column=1, columnspan=2, sticky="w")
            ttk.Separator(panel, orient="horizontal").grid(
                row=3, column=0, columnspan=3, sticky="ew", pady=3
            )
            ttk.Label(panel, text="Finger").grid(row=4, column=0, sticky="w")
            ttk.Label(panel, text="Deviation").grid(row=4, column=1, sticky="w")
            ttk.Label(panel, text="Score / class").grid(row=4, column=2, sticky="w")
            panel.columnconfigure(1, weight=1)
            for row, finger_name in enumerate(
                ("thumb", "index", "middle", "ring", "pinky"), start=5
            ):
                finger_value = tk.StringVar(value="—")
                bar = ttk.Progressbar(
                    panel, mode="determinate", maximum=75, length=100
                )
                values["fingers"][finger_name] = {
                    "text": finger_value,
                    "bar": bar,
                }
                ttk.Label(panel, text=finger_name.title()).grid(row=row, column=0, sticky="w")
                bar.grid(row=row, column=1, sticky="ew", padx=(3, 6), pady=2)
                ttk.Label(panel, textvariable=finger_value).grid(
                    row=row, column=2, sticky="w"
                )
            self.gesture_display[handedness] = values

        # Topic navigation stays on the left while the selected page fills the rest.
        self.settings_nav = ttk.Frame(settings_tab, width=148, padding=(8, 12, 8, 12))
        self.settings_nav.pack(side="left", fill="y")
        self.settings_nav.pack_propagate(False)
        ttk.Separator(settings_tab, orient="vertical").pack(side="left", fill="y")

        self.settings_content = ttk.Frame(settings_tab, padding=(18, 16, 16, 12))
        self.settings_content.pack(side="left", fill="both", expand=True)

        button_row = ttk.Frame(self.settings_content)
        button_row.pack(side="bottom", fill="x", pady=(12, 0))
        self.apply_button = ttk.Button(
            button_row, text="Apply", command=self.apply, style="Accent.TButton"
        )
        self.apply_button.pack(side="right")

        self.topic_title = tk.StringVar()
        self.topic_description = tk.StringVar()
        ttk.Label(
            self.settings_content, textvariable=self.topic_title,
            font=("TkDefaultFont", 12, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            self.settings_content, textvariable=self.topic_description,
            wraplength=240, justify="left",
        ).pack(anchor="w", pady=(4, 16))

        self.vars = {}
        self.topic_pages = {}
        topics = {
            "Tracking": ("Hand tracking behavior and diagnostics", [
                ("track_hands", "Track hands", None),
                ("profile", "Print FPS to console", None),
            ]),
            "Appearance": ("Choose the application theme and display scale", [
                ("theme", "Theme", THEMES),
                ("ui_scale", "UI scale", UI_SCALES),
            ]),
        }
        self.topic_descriptions = {}
        for topic, (description, items) in topics.items():
            page = ttk.Frame(self.settings_content)
            self.topic_pages[topic] = page
            self.topic_descriptions[topic] = description
            group = ttk.LabelFrame(page, text=topic, padding=(12, 8, 12, 10))
            group.pack(fill="x", anchor="n")
            for key, label, options in items:
                row = ttk.Frame(group)
                row.pack(fill="x", pady=8)
                if options is None:
                    var = tk.BooleanVar()
                    ttk.Checkbutton(
                        row, text=label, variable=var,
                        command=self._refresh_apply_state,
                    ).pack(anchor="w")
                else:
                    var = tk.StringVar()
                    ttk.Label(row, text=label).pack(anchor="w", pady=(0, 4))
                    combo = ttk.Combobox(
                        row, textvariable=var, values=options,
                        state="readonly", width=14,
                    )
                    combo.pack(anchor="w")
                    combo.bind(
                        "<<ComboboxSelected>>",
                        lambda e: self._refresh_apply_state(),
                    )
                self.vars[key] = var

        advanced_page = ttk.Frame(self.settings_content)
        self.topic_pages["Advanced"] = advanced_page
        advanced_group = ttk.LabelFrame(
            advanced_page, text="Advanced", padding=(12, 8, 12, 10)
        )
        advanced_group.pack(fill="x", anchor="n")
        ttk.Label(
            advanced_group, text="Settings file", font=("TkDefaultFont", 9, "bold")
        ).pack(anchor="w", pady=(0, 6))
        row = ttk.Frame(advanced_group)
        row.pack(fill="x")
        self.path_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.path_var, state="readonly").pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(row, text="Browse...", command=self.browse).pack(
            side="left", padx=(6, 0)
        )
        self.status_var = tk.StringVar()
        ttk.Label(advanced_group, textvariable=self.status_var, wraplength=240).pack(
            anchor="w", pady=(8, 0)
        )

        self.nav_buttons = {}
        self.nav_style = ttk.Style(self.root)
        self.nav_background = (
            self.nav_style.lookup("TFrame", "background")
            or self.root.cget("background")
        )
        self.nav_foreground = self.nav_style.lookup("TLabel", "foreground")
        self.nav_selected_background = self.nav_background
        self.nav_selected_foreground = self.nav_foreground
        topic_names = list(self.topic_pages)
        for index, topic in enumerate(topic_names):
            label = tk.Label(
                self.settings_nav, text=topic, takefocus=True, cursor="hand2",
                anchor="w", padx=12, pady=10, relief="flat", bd=0,
                background=self.nav_background, foreground=self.nav_foreground,
                activebackground=self.nav_background,
                activeforeground=self.nav_foreground,
                highlightthickness=0,
            )
            label.pack(fill="x", pady=(7, 7))
            label.bind("<Button-1>", lambda event, name=topic: self.show_topic(name))
            label.bind("<Return>", lambda event, name=topic: self.show_topic(name))
            label.bind("<space>", lambda event, name=topic: self.show_topic(name))
            self.nav_buttons[topic] = label
            if index < len(topic_names) - 1:
                ttk.Separator(self.settings_nav, orient="horizontal").pack(
                    fill="x", padx=8, pady=(0, 1)
                )

        self.current_topic = None
        self.show_topic("Tracking")
        self.show_settings(settings)
        self.status_var.set("Settings file loaded")

        # Watch tab switches so we can guard the Settings tab
        self._current_tab = self.notebook.select()
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.root.protocol("WM_DELETE_WINDOW", on_close)

    # ---- pending-change tracking ----

    def get_values(self):
        """Current widget values, as a dict of key -> value."""
        return SettingsData.from_dict({key: var.get() for key, var in self.vars.items()})

    def is_dirty(self):
        return self.get_values() != self._baseline

    def _refresh_apply_state(self):
        """Grey out Apply unless something differs from the baseline."""
        if self.is_dirty():
            self.apply_button.state(["!disabled"])
        else:
            self.apply_button.state(["disabled"])

    def show_topic(self, topic):
        """Display the selected settings topic in the content pane."""
        if self.current_topic:
            self.topic_pages[self.current_topic].pack_forget()
        self.current_topic = topic
        self.topic_title.set(topic)
        self.topic_description.set(self.topic_descriptions.get(topic, ""))
        self.topic_pages[topic].pack(fill="both", expand=True)
        for name, label in self.nav_buttons.items():
            label.configure(
                background=self.nav_selected_background if name == topic else self.nav_background,
                foreground=self.nav_selected_foreground if name == topic else self.nav_foreground,
                activebackground=self.nav_selected_background if name == topic else self.nav_background,
                activeforeground=self.nav_selected_foreground if name == topic else self.nav_foreground,
                font=("TkDefaultFont", 9, "bold" if name == topic else "normal"),
            )

    def switch_camera(self):
        """Queue a camera change without blocking Tk's event loop."""
        if self._camera_switching:
            return
        try:
            index = int(self.camera_var.get())
        except ValueError:
            self.camera_status.set("Select a camera device")
            return
        if index == self.camera_index and self._camera_active:
            self.camera_status.set(f"Using camera {index}")
            return
        if not self.on_camera_switch:
            self.camera_status.set("Camera switching is unavailable")
            return
        self._camera_switching = True
        self.camera_switch_button.state(["disabled"])
        self.camera_status.set(f"Opening camera {index}…")
        self.on_camera_switch(index)

    def update_camera_state(self, state, requested, active, message=None):
        """Reflect the capture worker's latest status in the camera controls."""
        if state in ("opening", "switching"):
            self._camera_switching = True
            self.camera_switch_button.state(["disabled"])
            self.camera_status.set(f"Opening camera {requested}…")
        elif state == "ready":
            self._camera_switching = False
            self._camera_active = True
            self.camera_switch_button.state(["!disabled"])
            self.camera_index = active
            self.camera_var.set(str(active))
            self.camera_status.set(message or f"Using camera {active}")
        elif state == "failed":
            self._camera_switching = False
            self._camera_active = False
            self.camera_switch_button.state(["!disabled"])
            if active is not None:
                self.camera_index = active
                self.camera_var.set(str(active))
            self.camera_status.set(message or f"Could not open camera {requested}")

    def update_gesture_display(self, hand_states, enabled=True):
        """Render the latest classified hand data in the Main tab."""
        if not enabled:
            self.gesture_enabled.set("Tracking disabled")
        elif not hand_states:
            self.gesture_enabled.set("No hands detected")
        else:
            self.gesture_enabled.set("Tracking active")

        for handedness, values in self.gesture_display.items():
            record = next(
                (item for item in hand_states if item["handedness"] == handedness),
                None,
            )
            if record is None:
                values["palm"].set("—")
                values["gesture"].set("—")
                values["pinch"].set("—")
                for finger_display in values["fingers"].values():
                    finger_display["text"].set("—")
                    finger_display["bar"].configure(value=0)
                continue

            state = record["state"]
            values["palm"].set(state.palm.value.replace("_", " ").title())
            values["gesture"].set(record["command"] or "—")
            if state.gesture is None:
                values["pinch"].set("No pinch")
            else:
                pinch = state.gesture
                values["pinch"].set(
                    f"d {pinch.distance:.3f}\n"
                    f"start ({pinch.start_pos[0]:.2f}, {pinch.start_pos[1]:.2f})\n"
                    f"now ({pinch.current_pos[0]:.2f}, {pinch.current_pos[1]:.2f})"
                )
            for finger_name, finger in state.fingers.items():
                finger_display = values["fingers"][finger_name]
                finger_display["text"].set(
                    f"{finger.deviation:.1f}° / {finger.position.value}"
                )
                finger_display["bar"].configure(
                    value=min(max(finger.deviation, 0.0), 75.0)
                )

    def show_settings(self, settings):
        """Refresh the path field and all widgets from a Settings object."""
        self.path_var.set(settings.path)
        for key, var in self.vars.items():
            value = getattr(settings.data, key)
            var.set(bool(value) if isinstance(var, tk.BooleanVar) else value)
        self._apply_display(settings.data.theme, settings.data.ui_scale)
        self._style_nav()
        self._baseline = self.get_values()  # whatever is shown now is the baseline
        self._refresh_apply_state()

    def apply(self):
        values = self.get_values()
        if self.on_apply:
            self.on_apply(values)
        self._apply_display(values.theme, values.ui_scale)
        self._style_nav()
        self._baseline = values
        self._refresh_apply_state()
        self.status_var.set("Settings applied and saved")

    def _style_nav(self):
        """Use Sun Valley's theme colors for normal and selected navigation rows."""
        active_theme = self.nav_style.theme_use()
        theme_suffix = "dark" if active_theme.endswith("dark") else "light"
        colors = f"::ttk::theme::sv_{theme_suffix}::colors"
        self.nav_background = self.root.tk.call("set", f"{colors}(-bg)")
        self.nav_foreground = self.root.tk.call("set", f"{colors}(-fg)")
        self.nav_selected_background = self.root.tk.call("set", f"{colors}(-selbg)")
        self.nav_selected_foreground = self.root.tk.call("set", f"{colors}(-selfg)")
        if self.current_topic:
            self.show_topic(self.current_topic)

    def discard(self):
        """Revert the widgets to the baseline."""
        for key, var in self.vars.items():
            var.set(getattr(self._baseline, key))
        self._refresh_apply_state()

    # ---- leaving the Settings tab ----

    def _on_tab_changed(self, event):
        old_tab = self._current_tab
        new_tab = self.notebook.select()
        self._current_tab = new_tab

        leaving_settings = old_tab == str(self.settings_tab) and new_tab != old_tab
        if leaving_settings and self.is_dirty():
            if not self._confirm_leave():
                # Cancel: go back to the Settings tab
                self._current_tab = old_tab
                self.notebook.select(old_tab)

    def _confirm_leave(self):
        """Ask what to do with pending changes. Returns False if the user cancels."""
        choice = UnappliedChangesDialog(self.root).show()
        if choice == "cancel":
            return False
        if choice == "apply":
            self.apply()
        else:
            self.discard()
        return True

    # ---- file browsing ----

    def browse(self):
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Select settings file",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:  # user cancelled
            return

        if not Settings.is_valid_path(path):
            self.status_var.set("Invalid: must be an existing .json file")
            return

        self.status_var.set("Settings file selected")
        if self.on_settings_path:
            self.on_settings_path(path)  # Application reloads and refreshes us

    def after(self, delay_ms, callback):
        self.root.after(delay_ms, callback)

    def run(self):
        self.root.mainloop()

    def quit(self):
        self.root.quit()

    def close(self):
        self.root.destroy()

    def _apply_display(self, theme, ui_scale):
        """Apply theme and UI scale; resize the window only if the scale changed."""
        scale = resolve_scale(self.root, ui_scale)
        apply_theme(self.root, theme, scale)
        if scale != self._scale:
            self._scale = scale
            self.root.geometry(
                f"{int(BASE_SIZE[0] * scale)}x{int(BASE_SIZE[1] * scale)}"
            )
