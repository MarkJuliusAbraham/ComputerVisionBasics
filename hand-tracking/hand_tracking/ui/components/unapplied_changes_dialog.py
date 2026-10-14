from tkinter import ttk
from hand_tracking.ui.core.modal_dialog import ModalDialog
from .theme import ThemeMetrics
from .buttons.discard_changes_button import DiscardChangesButton


class UnappliedChangesDialog:
    """Modal dialog asking what to do with unapplied changes."""

    def __init__(self, parent, context="Settings", action_label="Apply", *, return_label="Cancel"):
        self.parent = parent
        self.result = "cancel"
        self.context = context
        self.action_label = action_label
        self.action_result = "apply" if action_label == "Apply" else "save"

        self.modal = ModalDialog(parent, "Unsaved Changes", on_close=self._cancel)
        self.top = self.modal.window
        self.appearance = ThemeMetrics(self.top)
        self.heading_font = self.appearance.font_variant(size_delta=2, weight="bold")

        # Message
        body = ttk.Frame(self.top, padding=(24, 24, 24, 12))
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="You have unsaved changes", font=self.heading_font).pack(
            anchor="w"
        )
        ttk.Label(
            body,
            text=f"{action_label} or discard your changes to leave {context}.\n"
                 f"Choose {return_label} to keep editing.",
            justify="left",
        ).pack(anchor="w", pady=(6, 0))

        # Button row, right-aligned: action, Discard, return to editing.
        buttons = ttk.Frame(self.top, padding=(24, 8, 24, 20))
        buttons.pack(fill="x")
        ttk.Button(buttons, text=return_label, command=self._cancel).pack(side="right")
        DiscardChangesButton(buttons, text="Discard", command=self._discard).pack(
            side="right", padx=8
        )
        self.apply_button = ttk.Button(
            buttons, text=action_label, command=self._apply, default="active"
        )
        self.apply_button.pack(side="right")

        for button in buttons.winfo_children():
            button.bind("<Return>", self._on_return)
        self.top.bind("<Return>", self._on_return)

    def show(self):
        """Display modally and return the action, 'discard', or 'cancel'."""
        self.modal.show(initial_focus=self.apply_button)
        return self.result

    def _on_return(self, event):
        if isinstance(event.widget, ttk.Button):
            event.widget.invoke()
        else:
            self._apply()
        return "break"

    def _apply(self):
        self.result = self.action_result
        self.top.destroy()

    def _discard(self):
        self.result = "discard"
        self.top.destroy()

    def _cancel(self):
        self.result = "cancel"
        self.top.destroy()
