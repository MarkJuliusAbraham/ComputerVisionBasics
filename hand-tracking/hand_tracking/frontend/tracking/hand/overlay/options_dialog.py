"""Non-modal overlay preferences with live preview and explicit commits."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import tkinter as tk
from tkinter import ttk
from typing import cast

from hand_tracking.frontend.components.commit_actions import CommitActions
from hand_tracking.frontend.components.theme import ThemeMetrics
from hand_tracking.frontend.core.unsaved_changes_guard import PendingChanges, UnsavedChangesGuard
from hand_tracking.frontend.core.window_geometry import WindowGeometry
from hand_tracking.backend.settings.overlay_settings import (
    OVERLAY_STYLES,
    OverlayPosition,
    OverlaySettings,
    OverlayStyle,
)


class OverlayOptionsDialog:
    def __init__(
        self, parent: tk.Misc, preferences: OverlaySettings, *,
        on_preview: Callable[[OverlaySettings], None],
        on_save: Callable[[OverlaySettings], None],
        on_reposition: Callable[[bool], None], on_close: Callable[[], None],
        enabled: bool,
    ) -> None:
        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        self.window.title("Overlay settings")
        self.appearance = ThemeMetrics(self.window)
        self.geometry = WindowGeometry(self.window, (560, 380), minimum_size=(420, 300))
        self._saved = self._draft = preferences
        self._on_preview = on_preview
        self._on_save = on_save
        self._on_reposition = on_reposition
        self._on_close = on_close
        self._repositioning = False
        self._loading = True
        self.guard = UnsavedChangesGuard(self.window)
        self.pending = PendingChanges("Overlay settings", self.is_dirty, self.save, self.discard)
        pixels = self.appearance.pixels

        footer = ttk.Frame(self.window, padding=pixels(16))
        footer.pack(side="bottom", fill="x")
        ttk.Button(footer, text="Close", command=self.request_close).pack(
            side="bottom", anchor="e", pady=(pixels(12), 0),
        )
        self.actions = CommitActions(footer, on_save=self.save, on_discard=self.discard)
        self.actions.pack(fill="x")
        body = ttk.Frame(self.window, padding=pixels(16))
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Overlay style").pack(anchor="w")
        self.style = tk.StringVar(body, value=preferences.style)
        combo = ttk.Combobox(body, textvariable=self.style, values=OVERLAY_STYLES, state="readonly")
        combo.pack(fill="x", pady=(pixels(6), pixels(16)))
        combo.bind("<<ComboboxSelected>>", self._changed)

        ttk.Label(body, text="Background opacity").pack(anchor="w")
        opacity_row = ttk.Frame(body)
        opacity_row.pack(fill="x", pady=(pixels(6), pixels(6)))
        self.opacity = tk.DoubleVar(body, value=preferences.background_opacity * 100)
        self.opacity_text = tk.StringVar(body, value=f"{round(self.opacity.get())}%")
        ttk.Label(opacity_row, textvariable=self.opacity_text, width=5, anchor="e").pack(side="right")
        ttk.Scale(
            opacity_row, from_=0, to=100, variable=self.opacity, command=self._changed,
        ).pack(side="left", fill="x", expand=True, padx=(0, pixels(12)))
        ttk.Label(body, text="Text and deviation bars stay fully visible.").pack(anchor="w")

        self.reposition_button = ttk.Button(
            body, text="Reposition overlay", width=24, command=self._toggle_reposition,
        )
        self.reposition_button.pack(anchor="w", pady=(pixels(18), pixels(6)))
        self.position_hint = tk.StringVar(body)
        ttk.Label(body, textvariable=self.position_hint, wraplength=pixels(510), justify="left").pack(
            anchor="w",
        )
        self.set_enabled(enabled)
        self.window.protocol("WM_DELETE_WINDOW", self.request_close)
        self.window.bind("<Escape>", lambda _event: self.request_close())
        self.geometry.resize(self.appearance.scale)
        self.geometry.center_over(parent)
        self.window.deiconify()
        self._loading = False

    def is_dirty(self) -> bool:
        return self._draft != self._saved

    def _changed(self, _event=None) -> None:
        if self._loading:
            return
        percent = round(self.opacity.get())
        self.opacity_text.set(f"{percent}%")
        draft = replace(
            self._draft, style=cast(OverlayStyle, self.style.get()),
            background_opacity=percent / 100,
        )
        if draft != self._draft:
            self._draft = draft
            self._on_preview(draft)
            self.actions.set_dirty(self.is_dirty())

    def set_position(self, position: OverlayPosition) -> None:
        self._draft = replace(self._draft, position=position)
        self._on_preview(self._draft)
        self.actions.set_dirty(self.is_dirty())

    def set_enabled(self, enabled: bool) -> None:
        if not enabled:
            self._set_repositioning(False)
        self.reposition_button.state(["!disabled"] if enabled else ["disabled"])
        self.position_hint.set(
            "Drag the overlay, then click Done positioning. Save changes to remember its position."
            if enabled else "Enable the overlay in Debugging before repositioning it."
        )

    def _set_repositioning(self, active: bool) -> None:
        self._repositioning = active
        self._on_reposition(active)
        self.reposition_button.configure(
            text="Done positioning" if active else "Reposition overlay",
        )

    def _toggle_reposition(self) -> None:
        self._set_repositioning(not self._repositioning)

    def accept(self, preferences: OverlaySettings) -> None:
        self._loading = True
        self._saved = self._draft = preferences
        self.style.set(preferences.style)
        self.opacity.set(preferences.background_opacity * 100)
        self.opacity_text.set(f"{round(self.opacity.get())}%")
        self.actions.set_dirty(False)
        self._loading = False

    def save(self) -> bool:
        self._set_repositioning(False)
        try:
            self._on_save(self._draft)
        except (OSError, ValueError) as error:
            self.actions.set_status(f"Could not save: {error}", warning=True)
            return False
        self.accept(self._draft)
        self.actions.set_status("Saved")
        return True

    def discard(self) -> bool:
        self._set_repositioning(False)
        self._on_preview(self._saved)
        self.accept(self._saved)
        self.actions.set_status("Changes discarded")
        return True

    def confirm_close(self) -> bool:
        self._set_repositioning(False)
        return self.guard.confirm(self.pending, return_label="Cancel")

    def request_close(self) -> None:
        if self.confirm_close():
            self.destroy()

    def destroy(self) -> None:
        try:
            self._set_repositioning(False)
        finally:
            try:
                self.window.destroy()
            finally:
                self._on_close()
