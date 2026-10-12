import tkinter as tk
from tkinter import font, ttk
from .buttons import DiscardChangesButton


class UnappliedChangesDialog:
    """Modal dialog asking what to do with unapplied changes."""

    def __init__(self, parent, context="Settings", action_label="Apply", *, return_label="Cancel"):
        self.parent = parent
        self.result = "cancel"
        self.context = context
        self.action_label = action_label
        self.action_result = "apply" if action_label == "Apply" else "save"

        self.top = tk.Toplevel(parent)
        self.top.title("Unsaved Changes")
        self.top.transient(parent)
        self.top.resizable(False, False)
        self.top.protocol("WM_DELETE_WINDOW", self._cancel)

        self._bold = font.nametofont("TkDefaultFont").copy()
        self._bold.configure(weight="bold", size=11)

        # Message
        body = ttk.Frame(self.top, padding=(24, 24, 24, 12))
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="You have unsaved changes", font=self._bold).pack(
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
        self.top.bind("<Escape>", lambda e: self._cancel())

    def show(self):
        """Display modally and return the action, 'discard', or 'cancel'."""
        self._center()
        self.top.wait_visibility()
        self.top.grab_set()
        self.apply_button.focus_set()
        self.top.wait_window()
        return self.result

    def _center(self):
        self.top.update_idletasks()
        w, h = self.top.winfo_reqwidth(), self.top.winfo_reqheight()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - w) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - h) // 2
        self.top.geometry(f"+{max(x, 0)}+{max(y, 0)}")

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

