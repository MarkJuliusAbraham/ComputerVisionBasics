from copy import deepcopy
from dataclasses import replace
from itertools import product
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from uuid import uuid4

from gestures.finger_classifier import finger_categories
from gestures.gesture_config import (
    CommandSequence,
    CommandStep,
    GestureConfig,
    GestureDefinition,
    GestureMatch,
    RepeatSettings,
)
from gestures.profile_manager import GestureProfileManager
from control_panel.gesture_profile_picker import GestureProfilePickerDialog
from control_panel.gesture_manager_dialog import GestureManagerDialog


PALM_OPTIONS = {
    "Any": None,
    "Facing camera": "facing_camera",
    "Not facing camera": "not_facing_camera",
}
ALL_FINGER_CATEGORIES = finger_categories(6)
ALL_FINGER_OPTIONS = tuple(category.value for category in ALL_FINGER_CATEGORIES)
FINGER_NAMES = ("thumb", "index", "middle", "ring", "pinky")


def _build_straightness_options(categories):
    positions = [category.value for category in categories]
    options = {"Any position": None}
    for category in categories:
        options[category.label] = {category.value}
    if "straight" in positions and "partial" in positions:
        options["Straight or Partial"] = {"straight", "partial"}
    curled_positions = {
        category.value for category in categories
        if category.semantic_class == "curled"
    }
    if curled_positions:
        first_curled = min(positions.index(value) for value in curled_positions)
        options["Closed or Curled"] = set(positions[first_curled:])
    for start_category, label in (
        ("very_curled", "Very Curled or Closed"),
        ("nearly_closed", "Nearly Closed or Closed"),
    ):
        if start_category in positions:
            options[label] = set(positions[positions.index(start_category):])
    if positions:
        options["Not Straight"] = set(positions[1:])
        options["Not Closed"] = set(positions[:-1])
    return options


class MappingEditor(ttk.Frame):
    """Editor for saved gesture criteria and their command sequences."""

    def __init__(self, master, on_saved=None, config_path=None, segment_count=4):
        super().__init__(master, padding=(24, 20))
        self.categories = finger_categories(segment_count)
        self.finger_options = tuple(category.value for category in self.categories)
        self.straightness_options = _build_straightness_options(self.categories)
        self.profile_manager = GestureProfileManager()
        if config_path is not None:
            self.profile_manager.set_location(config_path)
        self.config_path = self.profile_manager.active_profile
        self.on_saved = on_saved
        self.config = GestureConfig.load(self.config_path)
        self._loading_form = False
        self._drafts = {
            definition.id: self._draft_from_definition(definition)
            for definition in self.config.definitions
        }
        self._definitions = list(self.config.definitions)
        self._baseline_definitions = list(self._definitions)
        self._baseline_drafts = deepcopy(self._drafts)
        self._repeat_baseline = self._repeat_draft_from_settings(
            self.config.repeat_settings
        )
        self._reset_baseline = self._reset_draft_from_match(self.config.reset_match)
        self._reset_draft = deepcopy(self._reset_baseline)
        self._shown_id = None
        self._labels_to_ids = self._build_label_map()

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 14))
        ttk.Label(
            header, text="Gesture mappings", font=("TkDefaultFont", 12, "bold")
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Choose the hand criteria that trigger each command. "
            "Rules must not overlap.",
            wraplength=660,
        ).pack(anchor="w", pady=(6, 0))

        profile_group = ttk.LabelFrame(self, text="Gesture Profile", padding=14)
        profile_group.pack(fill="x", pady=(0, 14))
        profile_row = ttk.Frame(profile_group)
        profile_row.pack(fill="x")
        profile_details = ttk.Frame(profile_row)
        profile_details.pack(side="left", fill="x", expand=True, padx=(0, 18))
        ttk.Label(
            profile_details, text="ACTIVE PROFILE", font=("TkDefaultFont", 8, "bold")
        ).pack(anchor="w")
        self.active_profile_name_var = tk.StringVar()
        ttk.Label(
            profile_details, textvariable=self.active_profile_name_var,
            font=("TkDefaultFont", 15, "bold"),
        ).pack(anchor="w", pady=(2, 1))
        profile_actions = ttk.Frame(profile_row)
        profile_actions.pack(side="right", anchor="center")
        ttk.Button(
            profile_actions, text="More Profiles", command=self._choose_profile
        ).pack(anchor="e", pady=(0, 6))
        self._update_active_profile_display()

        ttk.Separator(profile_group, orient="horizontal").pack(
            fill="x", pady=(12, 14)
        )

        criteria = ttk.LabelFrame(profile_group, text="Gesture", padding=14)
        criteria.pack(fill="x", pady=(0, 12))
        selection = ttk.Frame(criteria)
        selection.pack(fill="x", pady=(0, 14))
        ttk.Label(selection, text="Gesture").pack(side="left", padx=(0, 8))
        self.selected_id = tk.StringVar()
        self.selector = ttk.Combobox(
            selection,
            textvariable=self.selected_id,
            values=tuple(self._labels_to_ids),
            state="readonly",
            width=24,
        )
        self.selector.pack(side="left")
        self.selector.bind("<<ComboboxSelected>>", self._selection_changed)
        ttk.Button(
            selection, text="Manage Gestures", command=self._manage_gestures
        ).pack(side="right")

        hand_criteria = ttk.LabelFrame(criteria, text="Hand Criteria", padding=12)
        hand_criteria.pack(fill="x")
        hand_criteria_header = ttk.Frame(hand_criteria)
        hand_criteria_header.pack(fill="x", pady=(0, 12))
        palm_row = ttk.Frame(hand_criteria_header)
        palm_row.pack(side="left", anchor="nw")
        ttk.Label(palm_row, text="Palm orientation", width=18, anchor="w").pack(side="left")
        self.palm_var = tk.StringVar()
        self.palm_picker = ttk.Combobox(
            palm_row,
            textvariable=self.palm_var,
            values=tuple(PALM_OPTIONS),
            state="readonly",
            width=22,
        )
        self.palm_picker.pack(side="left")

        self.finger_mode = "straightness"
        self.finger_mode_button = ttk.Button(
            hand_criteria_header, text="Use classification checkboxes",
            command=self._toggle_finger_mode, width=30,
        )
        self.finger_mode_button.pack(side="right", anchor="ne")

        self.finger_options_area = ttk.Frame(hand_criteria)
        self.finger_options_area.pack(fill="x")
        self.finger_options_area.columnconfigure(0, weight=1)
        self.straightness_frame = ttk.Frame(self.finger_options_area)
        ttk.Label(self.straightness_frame, text="Finger", width=16, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        ttk.Label(self.straightness_frame, text="Straightness", anchor="w").grid(
            row=0, column=1, sticky="w", pady=(0, 4)
        )
        self.straightness_vars = {}
        self.straightness_combos = {}
        for row, name in enumerate(FINGER_NAMES, start=1):
            ttk.Label(self.straightness_frame, text=name.title(), width=16, anchor="w").grid(
                row=row, column=0, sticky="w", pady=4
            )
            variable = tk.StringVar(value="Any position")
            combo = ttk.Combobox(
                self.straightness_frame, textvariable=variable,
                values=tuple(self.straightness_options), state="readonly", width=24,
            )
            combo.grid(row=row, column=1, sticky="w", pady=4)
            self.straightness_vars[name] = variable
            self.straightness_combos[name] = combo

        self.classification_frame = ttk.Frame(self.finger_options_area)
        finger_grid = self.classification_frame
        ttk.Label(finger_grid, text="Finger", width=12, anchor="w").grid(
            row=0, column=0, sticky="w", padx=(0, 4)
        )
        self.category_column_widgets = {}
        for column, category in enumerate(ALL_FINGER_CATEGORIES, start=1):
            position = category.value
            header = ttk.Label(
                finger_grid, text=category.label, anchor="center"
            )
            header.grid(row=0, column=column, sticky="ew", padx=3)
            self.category_column_widgets[position] = [header]
            finger_grid.columnconfigure(column, weight=1, uniform="position")

        self.finger_vars = {}
        for row, name in enumerate(FINGER_NAMES, start=1):
            ttk.Label(finger_grid, text=name.title(), width=12, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(0, 6), pady=5
            )
            self.finger_vars[name] = {}
            for column, position in enumerate(ALL_FINGER_OPTIONS, start=1):
                variable = tk.BooleanVar()
                checkbox = ttk.Checkbutton(finger_grid, variable=variable)
                checkbox.grid(
                    row=row, column=column, padx=4, pady=5
                )
                self.category_column_widgets[position].append(checkbox)
                self.finger_vars[name][position] = variable

        self._update_category_widgets()

        self.straightness_frame.grid(row=0, column=0, sticky="ew")
        self.classification_frame.grid(row=0, column=0, sticky="ew")
        self.finger_options_area.update_idletasks()
        self.finger_options_area.configure(
            height=max(
                self.straightness_frame.winfo_reqheight(),
                self.classification_frame.winfo_reqheight(),
            ) + 4
        )
        self.classification_frame.grid_remove()
        self.finger_options_area.pack_propagate(False)
        self._refresh_finger_mode()

        tracked_finger_row = ttk.Frame(hand_criteria)
        tracked_finger_row.pack(fill="x", pady=(10, 0))
        ttk.Label(
            tracked_finger_row, text="Tracked fingertip", width=18, anchor="w"
        ).pack(side="left")
        self.tracked_finger_var = tk.StringVar(value="Index")
        ttk.Combobox(
            tracked_finger_row,
            textvariable=self.tracked_finger_var,
            values=("None", *(name.title() for name in FINGER_NAMES)),
            state="readonly",
            width=18,
        ).pack(side="left")

        commands = ttk.LabelFrame(
            profile_group, text="Command Sequence", padding=14
        )
        commands.pack(fill="x")
        command_row = ttk.Frame(commands)
        command_row.pack(fill="x")
        ttk.Label(command_row, text="Keys", width=18, anchor="w").pack(side="left")
        self.commands_var = tk.StringVar()
        ttk.Entry(command_row, textvariable=self.commands_var).pack(
            side="left", fill="x", expand=True
        )
        ttk.Label(
            commands, text="Enter one key per step, separated by commas."
        ).pack(anchor="w", pady=(6, 12))

        delay_row = ttk.Frame(commands)
        delay_row.pack(fill="x")
        ttk.Label(delay_row, text="Delay between steps (ms)", width=24, anchor="w").pack(
            side="left"
        )
        self.delay_var = tk.StringVar()
        ttk.Spinbox(
            delay_row, textvariable=self.delay_var, from_=0, to=10000,
            increment=50, width=10,
        ).pack(side="left")

        reset_group = ttk.LabelFrame(self, text="Reset Gesture", padding=14)
        reset_group.pack(fill="x", pady=(14, 0))
        ttk.Label(
            reset_group,
            text="Adjust the hand criteria that unlock tracking after a gesture.",
        ).pack(anchor="w", pady=(0, 8))
        reset_palm_row = ttk.Frame(reset_group)
        reset_palm_row.pack(fill="x", pady=(0, 6))
        ttk.Label(
            reset_palm_row, text="Palm orientation", width=16, anchor="w"
        ).pack(side="left")
        self.reset_palm_var = tk.StringVar()
        ttk.Combobox(
            reset_palm_row, textvariable=self.reset_palm_var,
            values=tuple(PALM_OPTIONS), state="readonly", width=22,
        ).pack(side="left")
        self.reset_finger_vars = {}
        self.reset_finger_combos = {}
        reset_mode_header = ttk.Frame(reset_group)
        reset_mode_header.pack(fill="x", pady=(0, 6))
        ttk.Label(reset_mode_header, text="Finger criteria").pack(side="left")
        self.reset_finger_mode = "straightness"
        self.reset_finger_mode_button = ttk.Button(
            reset_mode_header, text="Use classification checkboxes",
            command=self._toggle_reset_finger_mode, width=30,
        )
        self.reset_finger_mode_button.pack(side="right")
        self.reset_finger_options_area = ttk.Frame(reset_group)
        self.reset_finger_options_area.pack(fill="x")
        self.reset_finger_options_area.columnconfigure(0, weight=1)
        self.reset_straightness_frame = ttk.Frame(self.reset_finger_options_area)
        self.reset_category_column_widgets = {}
        self.reset_classification_frame = ttk.Frame(self.reset_finger_options_area)
        ttk.Label(
            self.reset_classification_frame, text="Finger", width=12, anchor="w"
        ).grid(row=0, column=0, sticky="w")
        for column, category in enumerate(ALL_FINGER_CATEGORIES, start=1):
            position = category.value
            header = ttk.Label(self.reset_classification_frame, text=category.label)
            header.grid(row=0, column=column, sticky="ew", padx=3)
            self.reset_category_column_widgets[position] = [header]
            self.reset_classification_frame.columnconfigure(
                column, weight=1, uniform="reset_position"
            )
        self.reset_classification_vars = {}
        for row_index, name in enumerate(FINGER_NAMES, start=1):
            ttk.Label(
                self.reset_classification_frame, text=name.title(), width=12, anchor="w"
            ).grid(row=row_index, column=0, sticky="w", pady=4)
            self.reset_classification_vars[name] = {}
            for column, position in enumerate(ALL_FINGER_OPTIONS, start=1):
                variable = tk.BooleanVar()
                checkbox = ttk.Checkbutton(self.reset_classification_frame, variable=variable)
                checkbox.grid(row=row_index, column=column, padx=4, pady=4)
                self.reset_category_column_widgets[position].append(checkbox)
                self.reset_classification_vars[name][position] = variable

        self._update_reset_category_widgets()
        for name in FINGER_NAMES:
            row = ttk.Frame(self.reset_straightness_frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=name.title(), width=16, anchor="w").pack(side="left")
            variable = tk.StringVar()
            combo = ttk.Combobox(
                row, textvariable=variable,
                values=tuple(self.straightness_options) + ("Custom classifications",),
                state="readonly", width=24,
            )
            combo.pack(side="left")
            self.reset_finger_vars[name] = variable
            self.reset_finger_combos[name] = combo
        self.reset_straightness_frame.pack(fill="x")
        self.reset_classification_frame.pack(fill="x")
        self.reset_classification_frame.pack_forget()
        self._load_reset_match(self._reset_draft)

        repeat_group = ttk.LabelFrame(self, text="Repeat Behavior", padding=14)
        repeat_group.pack(fill="x", pady=(14, 0))
        ttk.Label(
            repeat_group,
            text="Applies to every repeat-enabled gesture. The initial displacement "
                 "is a dead zone from gesture start; repeats then measure the drawn "
                 "fingertip path (0.09 = 9% of frame width).",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        repeat_rows = (
            ("Initial displacement before repeats", "initial_displacement", 0.0, 0.5, 0.01),
            ("Path distance between repeats", "distance_threshold", 0.01, 1.0, 0.01),
            ("Minimum repeat interval (ms)", "min_interval_ms", 0, 2000, 10),
            ("Maximum repeats per gesture", "max_repeats", 0, 20, 1),
        )
        self.repeat_vars = {}
        for row, (label, key, lower, upper, increment) in enumerate(repeat_rows, start=1):
            ttk.Label(repeat_group, text=label, width=32, anchor="w").grid(
                row=row, column=0, sticky="w", pady=4
            )
            variable = tk.StringVar()
            ttk.Spinbox(
                repeat_group, textvariable=variable, from_=lower, to=upper,
                increment=increment, width=12,
            ).grid(row=row, column=1, sticky="w", padx=(8, 0), pady=4)
            self.repeat_vars[key] = variable
        self._load_repeat_settings(self._repeat_baseline)

        footer = ttk.Frame(self)
        footer.pack(side="bottom", fill="x", pady=(12, 0))
        self.status = tk.StringVar(value="Gesture mappings loaded")
        ttk.Label(footer, textvariable=self.status, wraplength=500).pack(
            side="left", fill="x", expand=True
        )
        self.save_button = ttk.Button(
            footer, text="Save mappings", command=self.save,
            style="Accent.TButton",
        )
        self.save_button.pack(side="right")

        for variable in (
            self.palm_var, self.commands_var, self.delay_var,
            self.tracked_finger_var,
            *self.repeat_vars.values(),
            self.reset_palm_var,
            *self.reset_finger_vars.values(),
            *(var for group in self.reset_classification_vars.values() for var in group.values()),
            *(var for group in self.finger_vars.values() for var in group.values()),
            *self.straightness_vars.values(),
        ):
            variable.trace_add("write", lambda *_: self._editor_changed())

        if self._drafts:
            first = next(iter(self._drafts))
            self._shown_id = first
            self.selected_id.set(self._label_for_id(first))
            self._load_draft(self._drafts[first])
        self._refresh_save_state()

    def set_segment_count(self, segment_count):
        """Refresh available profile criteria to match the active classifier."""
        self._capture_draft()
        self._capture_reset_match()
        self.categories = finger_categories(segment_count)
        self.finger_options = tuple(category.value for category in self.categories)
        self.straightness_options = _build_straightness_options(self.categories)
        for combo in self.straightness_combos.values():
            combo.configure(values=tuple(self.straightness_options))
        for combo in self.reset_finger_combos.values():
            combo.configure(
                values=tuple(self.straightness_options) + ("Custom classifications",)
            )
        self._update_category_widgets()
        self._update_reset_category_widgets()
        self._load_reset_match(self._reset_draft)
        self._refresh_reset_finger_mode()
        if self._shown_id is not None:
            self._load_draft(self._drafts[self._shown_id])

    def _update_category_widgets(self):
        active = set(self.finger_options)
        for column, (position, widgets) in enumerate(
            self.category_column_widgets.items(), start=1
        ):
            self.classification_frame.columnconfigure(
                column, weight=1 if position in active else 0
            )
            for widget in widgets:
                if position in active:
                    widget.grid()
                else:
                    widget.grid_remove()

    def _update_reset_category_widgets(self):
        active = set(self.finger_options)
        for column, (position, widgets) in enumerate(
            self.reset_category_column_widgets.items(), start=1
        ):
            self.reset_classification_frame.columnconfigure(
                column, weight=1 if position in active else 0
            )
            for widget in widgets:
                if position in active:
                    widget.grid()
                else:
                    widget.grid_remove()

    def _label_for_id(self, gesture_id):
        if hasattr(self, "_labels_to_ids"):
            for label, current_id in self._labels_to_ids.items():
                if current_id == gesture_id:
                    return label
        return self._drafts[gesture_id]["name"] or "Unnamed"

    def _build_label_map(self):
        labels = {}
        occurrences = {}
        for gesture_id, draft in self._drafts.items():
            name = draft["name"] or "Unnamed"
            key = name.casefold()
            occurrences[key] = occurrences.get(key, 0) + 1
            label = name if occurrences[key] == 1 else f"{name} ({occurrences[key]})"
            while label in labels:
                occurrences[key] += 1
                label = f"{name} ({occurrences[key]})"
            labels[label] = gesture_id
        return labels

    @staticmethod
    def _draft_from_definition(definition):
        return {
            "name": definition.name,
            "palm": definition.match.palm,
            "fingers": {
                name: set(definition.match.fingers.get(name, ()))
                for name in FINGER_NAMES
            },
            "commands": ", ".join(step.value for step in definition.commands.steps),
            "delay": str(definition.commands.delay_ms_between_steps),
            "tracked_finger": definition.tracked_finger,
        }

    @staticmethod
    def _repeat_draft_from_settings(settings):
        return {
            "initial_displacement": str(settings.initial_displacement),
            "distance_threshold": str(settings.distance_threshold),
            "min_interval_ms": str(round(settings.min_interval_seconds * 1000)),
            "max_repeats": str(settings.max_repeats),
        }

    @staticmethod
    def _reset_draft_from_match(match):
        return {
            "palm": match.palm,
            "fingers": {
                name: set(match.fingers.get(name, ())) for name in FINGER_NAMES
            },
        }

    def _load_reset_match(self, draft):
        self._loading_form = True
        self.reset_palm_var.set(next(
            label for label, value in PALM_OPTIONS.items() if value == draft["palm"]
        ))
        for name, variable in self.reset_finger_vars.items():
            selected = draft["fingers"][name]
            for position, checkbox in self.reset_classification_vars[name].items():
                checkbox.set(position in selected)
            label = next(
                (
                    option for option, positions in self.straightness_options.items()
                    if (not selected if positions is None else selected == positions)
                ),
                "Custom classifications",
            )
            variable.set(label)
        self._loading_form = False

    def _capture_reset_match(self):
        self._reset_draft["palm"] = PALM_OPTIONS[self.reset_palm_var.get()]
        if self.reset_finger_mode == "classifications":
            for name, variables in self.reset_classification_vars.items():
                self._reset_draft["fingers"][name] = {
                    position for position, variable in variables.items()
                    if variable.get() and position in self.finger_options
                }
        else:
            for name, variable in self.reset_finger_vars.items():
                label = variable.get()
                if label == "Custom classifications":
                    continue
                positions = self.straightness_options[label]
                self._reset_draft["fingers"][name] = (
                    set() if positions is None else set(positions)
                )
        return self._reset_draft

    def _toggle_reset_finger_mode(self):
        self._capture_reset_match()
        self.reset_finger_mode = (
            "classifications" if self.reset_finger_mode == "straightness"
            else "straightness"
        )
        self._load_reset_match(self._reset_draft)
        self._refresh_reset_finger_mode()
        self._refresh_save_state()

    def _refresh_reset_finger_mode(self):
        if self.reset_finger_mode == "straightness":
            self.reset_classification_frame.pack_forget()
            self.reset_straightness_frame.pack(fill="x")
            self.reset_finger_mode_button.configure(
                text="Use classification checkboxes"
            )
        else:
            self.reset_straightness_frame.pack_forget()
            self.reset_classification_frame.pack(fill="x")
            self.reset_finger_mode_button.configure(
                text="Use straightness controls"
            )

    def _load_repeat_settings(self, draft):
        self._loading_form = True
        for key, variable in self.repeat_vars.items():
            variable.set(draft[key])
        self._loading_form = False

    def _capture_repeat_settings(self):
        return {key: variable.get() for key, variable in self.repeat_vars.items()}

    def _capture_draft(self):
        gesture_id = self._shown_id
        if not gesture_id:
            return
        palm = PALM_OPTIONS[self.palm_var.get()]
        fingers = self._current_finger_selections()
        self._drafts[gesture_id] = {
            "name": self._drafts[gesture_id]["name"],
            "palm": palm,
            "fingers": fingers,
            "commands": self.commands_var.get(),
            "delay": self.delay_var.get(),
            "tracked_finger": (
                None if self.tracked_finger_var.get() == "None"
                else self.tracked_finger_var.get().lower()
            ),
        }

    def is_dirty(self):
        self._capture_draft()
        self._capture_reset_match()
        return (
            self._drafts != self._baseline_drafts
            or self._definitions != self._baseline_definitions
            or self._capture_repeat_settings() != self._repeat_baseline
            or self._reset_draft != self._reset_baseline
        )

    def _refresh_save_state(self):
        self.save_button.state(
            ["!disabled"] if self.is_dirty() else ["disabled"]
        )

    def discard(self):
        self._drafts = deepcopy(self._baseline_drafts)
        self._definitions = list(self._baseline_definitions)
        self._load_repeat_settings(self._repeat_baseline)
        self._reset_draft = deepcopy(self._reset_baseline)
        self._load_reset_match(self._reset_draft)
        self._labels_to_ids = self._build_label_map()
        self.selector.configure(values=tuple(self._labels_to_ids))
        if self._shown_id not in self._drafts:
            self._shown_id = next(iter(self._drafts), None)
        if self._shown_id is not None:
            self.selected_id.set(self._label_for_id(self._shown_id))
            self._load_draft(self._drafts[self._shown_id])
        self.status.set("Unsaved mapping changes discarded")
        self._refresh_save_state()

    def _load_draft(self, draft):
        self._loading_form = True
        palm_label = next(
            label for label, value in PALM_OPTIONS.items()
            if value == draft["palm"]
        )
        self.palm_var.set(palm_label)
        for name, variables in self.finger_vars.items():
            selected = draft["fingers"][name]
            for position, variable in variables.items():
                variable.set(position in selected)
            label = next(
                (
                    option for option, positions in self.straightness_options.items()
                    if (not selected if positions is None else selected == positions)
                ),
                "Custom classifications",
            )
            self.straightness_vars[name].set(label)
        self.commands_var.set(draft["commands"])
        self.delay_var.set(draft["delay"])
        self.tracked_finger_var.set(
            draft["tracked_finger"].title()
            if draft["tracked_finger"] else "None"
        )
        self._loading_form = False

    def _current_finger_selections(self):
        if self.finger_mode == "classifications":
            return {
                name: {
                    position for position, variable in variables.items()
                    if variable.get()
                }
                for name, variables in self.finger_vars.items()
            }
        current = self._drafts.get(self._shown_id, {}).get("fingers", {})
        result = {}
        for name, variable in self.straightness_vars.items():
            label = variable.get()
            if label == "Custom classifications":
                result[name] = set(current.get(name, ()))
            else:
                positions = self.straightness_options[label]
                result[name] = set() if positions is None else set(positions)
        return result

    def _toggle_finger_mode(self):
        self._capture_draft()
        if self._shown_id is not None:
            self._sync_finger_controls(self._drafts[self._shown_id])
        self.finger_mode = (
            "classifications" if self.finger_mode == "straightness"
            else "straightness"
        )
        self._refresh_finger_mode()

    def _refresh_finger_mode(self):
        if self.finger_mode == "straightness":
            if self.classification_frame.winfo_manager() == "grid":
                self.classification_frame.grid_remove()
            self.straightness_frame.grid(row=0, column=0, sticky="ew")
            self.finger_mode_button.configure(text="Use classification checkboxes")
        else:
            if self.straightness_frame.winfo_manager() == "grid":
                self.straightness_frame.grid_remove()
            self.classification_frame.grid(row=0, column=0, sticky="ew")
            self.finger_mode_button.configure(text="Use straightness controls")

    def _sync_finger_controls(self, draft):
        self._loading_form = True
        for name, selected in draft["fingers"].items():
            for position, variable in self.finger_vars[name].items():
                variable.set(position in selected)
            label = next(
                (
                    option for option, positions in self.straightness_options.items()
                    if (not selected if positions is None else selected == positions)
                ),
                "Custom classifications",
            )
            self.straightness_vars[name].set(label)
        self._loading_form = False

    def _editor_changed(self):
        if self._loading_form:
            return
        if self._shown_id is not None:
            self._capture_draft()
            self._sync_finger_controls(self._drafts[self._shown_id])
            self._labels_to_ids = self._build_label_map()
            self.selector.configure(values=tuple(self._labels_to_ids))
            self.selected_id.set(self._label_for_id(self._shown_id))
        self._capture_reset_match()
        self._refresh_save_state()

    def _manage_gestures(self):
        GestureManagerDialog(
            self.winfo_toplevel(),
            gestures=self._definitions,
            on_create=self._create_gesture,
            on_save=self._save_managed_gestures,
        ).show()

    def _create_gesture(self, current_definitions):
        existing = [definition.match for definition in current_definitions]
        new_match = None
        for palm in (None, "facing_camera", "not_facing_camera"):
            for positions in product(self.finger_options, repeat=len(FINGER_NAMES)):
                match = GestureMatch(
                    palm=palm,
                    fingers={finger: frozenset((position,))
                             for finger, position in zip(FINGER_NAMES, positions)},
                )
                if all(
                    not GestureConfig.matches_can_overlap(match, current)
                    for current in existing
                ):
                    new_match = match
                    break
            if new_match is not None:
                break
        if new_match is None:
            raise ValueError("No non-overlapping gesture pattern is available")

        gesture_id = f"gesture_{uuid4().hex[:8]}"
        current_ids = {definition.id for definition in current_definitions}
        while gesture_id in current_ids:
            gesture_id = f"gesture_{uuid4().hex[:8]}"
        return GestureDefinition(
            id=gesture_id,
            name="New Gesture",
            match=new_match,
            commands=CommandSequence((CommandStep(type="key_tap", value="a"),)),
            tracked_finger="index",
        )

    def _save_managed_gestures(self, staged_definitions, selected_id=None):
        if not staged_definitions:
            raise ValueError("A profile must contain at least one gesture")
        ids = [definition.id for definition in staged_definitions]
        if len(ids) != len(set(ids)):
            raise ValueError("Gesture IDs must be unique")

        saved_by_id = {definition.id: definition for definition in self.config.definitions}
        definitions = []
        for staged in staged_definitions:
            name = staged.name.strip()
            if not name:
                raise ValueError("Gesture names cannot be empty")
            base = saved_by_id.get(staged.id, staged)
            definitions.append(replace(base, name=name))

        updated_config = replace(self.config, definitions=tuple(definitions))
        GestureConfig._validate_no_overlaps(updated_config.definitions)
        updated_config.save(self.config_path)

        previous_drafts = self._drafts
        previous_baseline = self._baseline_drafts
        self._drafts = {}
        self._baseline_drafts = {}
        for definition in definitions:
            if definition.id in previous_drafts:
                draft = deepcopy(previous_drafts[definition.id])
                baseline = deepcopy(previous_baseline[definition.id])
                draft["name"] = definition.name
                baseline["name"] = definition.name
            else:
                draft = self._draft_from_definition(definition)
                baseline = deepcopy(draft)
            self._drafts[definition.id] = draft
            self._baseline_drafts[definition.id] = baseline

        self.config = updated_config
        self._definitions = list(definitions)
        self._baseline_definitions = list(definitions)
        self._labels_to_ids = self._build_label_map()
        if selected_id in self._drafts:
            self._shown_id = selected_id
        if self._shown_id not in self._drafts:
            self._shown_id = next(iter(self._drafts), None)
        self.selector.configure(values=tuple(self._labels_to_ids))
        if self._shown_id is not None:
            self.selected_id.set(self._label_for_id(self._shown_id))
            self._load_draft(self._drafts[self._shown_id])
        self.status.set(
            "Gestures saved; mapping edits remain unsaved"
            if self._drafts != self._baseline_drafts
            else "Gestures saved"
        )
        self._refresh_save_state()
        if self.on_saved:
            self.on_saved(updated_config)

    def _selection_changed(self, _event=None):
        self._capture_draft()
        self._refresh_save_state()
        self._shown_id = self._labels_to_ids[self.selected_id.get()]
        self._load_draft(self._drafts[self._shown_id])

    def _build_config(self):
        self._capture_draft()
        definitions = []
        for definition in self._definitions:
            draft = self._drafts[definition.id]
            if not draft["name"]:
                raise ValueError(f"{definition.id}: gesture name cannot be empty")
            fingers = {
                name: frozenset(positions)
                for name, positions in draft["fingers"].items()
                if positions
            }
            match = GestureMatch(palm=draft["palm"], fingers=fingers)

            command_values = [
                value.strip() for value in draft["commands"].split(",")
            ]
            if not command_values or any(
                len(value) != 1 for value in command_values
            ):
                raise ValueError(
                    f"{definition.id}: enter one character for each command step"
                )
            try:
                delay = int(draft["delay"])
            except (TypeError, ValueError) as error:
                raise ValueError("Delay must be a whole number of milliseconds") from error
            if delay < 0:
                raise ValueError("Delay cannot be negative")

            commands = CommandSequence(
                steps=tuple(
                    CommandStep(type="key_tap", value=value)
                    for value in command_values
                ),
                delay_ms_between_steps=delay,
            )
            definitions.append(replace(
                definition,
                name=draft["name"],
                match=match,
                commands=commands,
                tracked_finger=draft["tracked_finger"],
            ))

        repeat_draft = self._capture_repeat_settings()
        try:
            repeat_settings = RepeatSettings.from_dict({
                "initial_displacement": float(repeat_draft["initial_displacement"]),
                "distance_threshold": float(repeat_draft["distance_threshold"]),
                "min_interval_seconds": float(repeat_draft["min_interval_ms"]) / 1000,
                "max_repeats": int(repeat_draft["max_repeats"]),
            })
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid repeat behavior setting: {error}") from error
        config = replace(
            self.config, definitions=tuple(definitions),
            repeat_settings=repeat_settings,
            reset_match=GestureMatch(
                palm=self._capture_reset_match()["palm"],
                fingers={
                    name: frozenset(positions)
                    for name, positions in self._reset_draft["fingers"].items()
                    if positions
                },
            ),
        )
        if config.reset_match.palm is None and not config.reset_match.fingers:
            raise ValueError("Reset gesture must constrain palm orientation or at least one finger")
        GestureConfig._validate_no_overlaps(config.definitions)
        return config

    def _confirm_profile_change(self):
        if not self.is_dirty():
            return True
        from control_panel.unapplied_changes_dialog import UnappliedChangesDialog

        choice = UnappliedChangesDialog(
            self.winfo_toplevel(), context="Mapping", action_label="Save"
        ).show()
        if choice == "save":
            return self.save()
        if choice == "discard":
            self.discard()
            return True
        return False

    def _activate_profile(self, path, source_folder=None):
        if not self._confirm_profile_change():
            return False
        try:
            config = GestureConfig.load(path)
            if source_folder is not None:
                self.profile_manager.set_location(source_folder)
            self.profile_manager.select_profile(path)
        except (ValueError, OSError) as error:
            self.status.set(f"Could not load profile: {error}")
            return False
        self.config_path = str(path)
        self.config = config
        self._drafts = {
            definition.id: self._draft_from_definition(definition)
            for definition in config.definitions
        }
        self._definitions = list(config.definitions)
        self._baseline_definitions = list(self._definitions)
        self._baseline_drafts = deepcopy(self._drafts)
        self._repeat_baseline = self._repeat_draft_from_settings(
            config.repeat_settings
        )
        self._reset_baseline = self._reset_draft_from_match(config.reset_match)
        self._reset_draft = deepcopy(self._reset_baseline)
        self._load_reset_match(self._reset_draft)
        self._load_repeat_settings(self._repeat_baseline)
        self._labels_to_ids = self._build_label_map()
        self._shown_id = next(iter(self._drafts), None)
        self.selector.configure(values=tuple(self._labels_to_ids))
        if self._shown_id:
            self.selected_id.set(self._label_for_id(self._shown_id))
            self._load_draft(self._drafts[self._shown_id])
        self._update_active_profile_display()
        self.status.set(f"Active profile: {Path(self.config_path).name}")
        self._refresh_save_state()
        if self.on_saved:
            self.on_saved(config)
        return True

    def _choose_profile(self):
        dialog = GestureProfilePickerDialog(
            self.winfo_toplevel(),
            initial_folder=self.profile_manager._folder_for(
                self.profile_manager.source_path
            ),
            active_profile=self.profile_manager.active_profile,
            on_create_profile=self._create_profile_in_folder,
        )
        selection = dialog.show()
        if selection is None:
            return
        profile, folder = selection
        self._activate_profile(profile, source_folder=folder)

    def _create_profile_in_folder(self, folder, profile_name):
        path = Path(folder) / f"{profile_name}.json"
        if path.exists():
            raise ValueError(f"A profile named {profile_name!r} already exists")
        config = self._build_config()
        config.save(path)
        return path

    def _update_active_profile_display(self):
        profile = Path(self.config_path)
        display_name = profile.stem.replace("_", " ").replace("-", " ").title()
        self.active_profile_name_var.set(display_name or profile.name)

    def save(self):
        try:
            config = self._build_config()
            config.save(self.config_path)
        except (ValueError, OSError) as error:
            self.status.set(f"Could not save mappings: {error}")
            return False

        self.config = config
        self._drafts = {
            definition.id: self._draft_from_definition(definition)
            for definition in config.definitions
        }
        self._definitions = list(config.definitions)
        self._baseline_definitions = list(self._definitions)
        self._baseline_drafts = deepcopy(self._drafts)
        self._repeat_baseline = self._repeat_draft_from_settings(
            config.repeat_settings
        )
        self._reset_baseline = self._reset_draft_from_match(config.reset_match)
        self._reset_draft = deepcopy(self._reset_baseline)
        self._load_reset_match(self._reset_draft)
        self._load_repeat_settings(self._repeat_baseline)
        self._labels_to_ids = self._build_label_map()
        if self._shown_id is not None:
            self.selector.configure(values=tuple(self._labels_to_ids))
            self.selected_id.set(self._label_for_id(self._shown_id))
        self.status.set("Gesture mappings saved")
        self._refresh_save_state()
        if self.on_saved:
            self.on_saved(config)
        return True
