"""Profile header, gesture browser, focused editor, and persistent actions."""

from tkinter import ttk
from gui_tkinter.core.idle_refresh import IdleRefresh

from gestures.gesture_validation import GestureValidationReport
from gui_tkinter.components.scrollable_frame import ScrollableFrame
from gui_tkinter.components.theme import ThemeMetrics

from .sections.gesture_editor import GestureEditorSection
from .sections.gesture_list import GestureListSection
from .sections.mapping_footer import MappingFooter
from .sections.profile import ProfileSection
from .mapping_callbacks import MappingCallbacks


class MappingForm(ttk.Frame):
    def __init__(
        self, master, *, callbacks: MappingCallbacks, segment_count=4,
    ):
        super().__init__(master)
        self.appearance = ThemeMetrics(self)
        self._reset_match = None
        self._selected_id = None
        self._validation = GestureValidationReport({})
        self.profile = ProfileSection(self, on_choose=callbacks.on_choose_profile)
        self.profile.pack(fill="x", pady=(0, self.appearance.pixels(16)))
        self.divider = ttk.Separator(self)
        self.divider.pack(fill="x", pady=(0, self.appearance.pixels(16)))
        self.footer = MappingFooter(self, self.appearance, callbacks.on_save, callbacks.on_discard)
        self.footer.pack(side="bottom", fill="x", pady=(self.appearance.pixels(16), 0))
        workspace = ttk.Frame(self)
        workspace.pack(fill="both", expand=True)
        workspace.columnconfigure(1, weight=1)
        workspace.rowconfigure(0, weight=1)
        self.browser = GestureListSection(
            workspace, self.appearance, on_select=callbacks.on_select,
            on_manage=callbacks.on_manage, on_reset=callbacks.on_edit_reset,
            on_rename=callbacks.on_rename, on_delete=callbacks.on_delete,
        )
        self.browser.grid(row=0, column=0, sticky="ns", padx=(0, self.appearance.pixels(20)))
        self.scroll = ScrollableFrame(workspace)
        self.scroll.grid(row=0, column=1, sticky="nsew")
        self.editor = GestureEditorSection(
            self.scroll.content, self.appearance, callbacks.on_change, segment_count,
            on_repeat_change=callbacks.on_repeat_change,
        )
        self.editor.pack(fill="x", padx=(0, self.appearance.pixels(8)))
        self._refresh_layout()
        self.theme_refresh = IdleRefresh(self, self._refresh_layout, event="<<ThemeChanged>>")

    def _refresh_layout(self):
        self.appearance.refresh()
        pixels = self.appearance.pixels
        self.configure(padding=pixels(16))
        self.profile.pack_configure(pady=(0, pixels(16)))
        self.divider.pack_configure(pady=(0, pixels(16)))
        self.footer.pack_configure(pady=(pixels(16), 0))
        self.browser.grid_configure(padx=(0, pixels(20)))
        self.editor.pack_configure(padx=(0, pixels(8)))

    @property
    def segment_count(self):
        return self.editor.segment_count

    def set_segment_count(self, segment_count):
        self.editor.set_segment_count(segment_count)

    def reset_values(self):
        return self._reset_match

    def load_reset(self, match):
        self._reset_match = match

    def values(self):
        return self.editor.values()

    def repeat_values(self):
        return self.editor.repeats.values()

    def applies_repeats_to_all(self):
        return self.editor.repeats.apply_to_all.get()

    def load_draft(self, draft):
        self.editor.load(draft)

    def show_profile(self, path):
        self.profile.load(path)

    def show_gestures(self, definitions, selected_id, validation=None):
        # Replace the report together with the profile's names so a previous
        # profile's peer IDs cannot leak into the new selected heading.
        self._validation = validation if validation is not None else GestureValidationReport({})
        self.browser.load(definitions, selected_id)
        self.browser.show_validation(self._validation.invalid_ids)
        self.show_selected_gesture(selected_id)

    def show_selected_gesture(self, gesture_id):
        self._selected_id = gesture_id
        self.editor.show_gesture(self.browser.display_name(gesture_id))
        self._show_conflict()

    def show_validation(self, report):
        self._validation = report
        self.browser.show_validation(report.invalid_ids)
        self._show_conflict()

    def _show_conflict(self):
        self.editor.show_conflict(
            self._validation.conflict_for(self._selected_id), self.browser.display_names,
        )

    def set_dirty(self, dirty):
        self.footer.set_dirty(dirty)

    def set_status(self, message):
        self.footer.set_status(message)
