# Runtime failures and shutdown

Topmost overlays are withdrawn as soon as quitting or fatal frame failure
begins, before native worker cleanup. Shutdown then releases gesture input,
requests model/camera cleanup, destroys Tk windows, and closes the preview.
Cleanup attempts all remaining resources even if one step raises an exception.
Overlay windows are destroyed before releasing their graphics resources.
Partially built hub windows also destroy their Tk root if construction fails.

The model loader leases sessions with a reference count. Its management lock
protects only metadata; native inference runs outside that lock. Retired models
are closed on the loader worker only after all submission leases finish.
Shutdown stops new leases immediately and waits at most one second for the
worker. Camera and preview workers each wait at most two seconds and log if
still alive. These limits do not forcibly interrupt native code: daemon workers
can complete later, and a process restart is required if native code remains
stuck. A force-killed process cannot execute Python cleanup.

Unexpected frame or Tk callback errors stop tracking and commands, hide
overlays, display the error, and exit through normal cleanup. A failed frame
cannot silently leave the application open with no future frame scheduled.
Expected validation and recoverable model-loading errors retain their existing
handling. New frame callbacks are scheduled only after processing and profiler
completion succeed.

## Diagnostic files

The entry point owns `RuntimeDiagnostics` for the whole application run:

- `logs/application.log`: errors with tracebacks, shutdown messages, worker
  timeouts, and the process/UI-thread identities. Rotates at approximately
  2 MB, retaining three backups.
- `logs/thread-dumps.log`: all Python thread stacks after ten seconds without
  UI timer progress; records once per stall, then rearms after recovery.
  Native fatal faults also use this file when diagnostics owns faulthandler.

The heartbeat is a recurring Tk timer so expected modal dialog interaction
does not by itself count as stalled frame processing. The watchdog never
touches Tk. It cannot run if native code indefinitely holds the Python GIL,
and a hard kill may leave no final log entry. Diagnostic setup failures are
reported without preventing startup. Logs are excluded from Git.

If the black layer recurs, preserve both log files and note whether the logged
Python PID is still running. A live topmost window, a Windows ghost window,
and a compositor artifact need different follow-up investigations. The fixes
address observed lifecycle weaknesses; the original intermittent black layer
has not been reproduced or conclusively attributed.
