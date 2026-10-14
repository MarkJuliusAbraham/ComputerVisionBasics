"""A notebook that asks permission before changing its selected page."""

from tkinter import ttk


_DISPATCH_COMMAND = "::gui_tkinter::guarded_notebook::dispatch"
_DISPATCH_SCRIPT = """
namespace eval ::gui_tkinter::guarded_notebook {}
proc ::gui_tkinter::guarded_notebook::dispatch {native guard args} {
    if {[llength $args] == 2 && [lindex $args 0] eq "select"} {
        set requested [lindex $args 1]
        set current [$native select]
        set state [$native tab $requested -state]
        set target [lindex [$native tabs] [$native index $requested]]
        if {$current ne "" && $current ne $target && $state ne "disabled"} {
            if {![$guard $current $target]} {
                return ""
            }
        }
    }
    tailcall $native {*}$args
}
"""


class GuardedNotebook(ttk.Notebook):
    def __init__(self, master, *, before_select=None, **kwargs):
        super().__init__(master, **kwargs)
        self.before_select = before_select
        self._selecting = False
        self._widget_command = f"{self._w}_native"
        # Tk's mouse and keyboard bindings call the Tcl widget command directly.
        # Keep native operations in Tcl: theme palette updates deliberately
        # catch unsupported color options, which must not raise through Python.
        self.tk.eval(_DISPATCH_SCRIPT)
        self._guard_command = self._register(self._can_select)
        self.tk.call("rename", self._w, self._widget_command)
        self.tk.call(
            "interp", "alias", "", self._w, "", _DISPATCH_COMMAND,
            self._widget_command, self._guard_command,
        )
        self.bind("<Destroy>", self._destroyed, add="+")

    def _can_select(self, current, target):
        # Modal dialogs process events; ignore additional navigation while one
        # selection is being confirmed, rather than opening another prompt.
        if self._selecting:
            return False

        self._selecting = True
        try:
            return self.before_select is None or bool(self.before_select(current, target))
        except Exception:
            # Report callback failures normally and keep the draft visible.
            self._report_exception()
            return False
        finally:
            self._selecting = False

    def _destroyed(self, event):
        if event.widget is self:
            self.before_select = None
            # Tk removes the native command; we own the alias and guard callback.
            self.tk.call("interp", "alias", "", self._w, "")
            self.deletecommand(self._guard_command)
