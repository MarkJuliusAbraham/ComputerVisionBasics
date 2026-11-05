"""Run Python's cyclic garbage collector only on the Tk thread.

tkinter objects such as Font, Variable and PhotoImage delete their Tcl
counterparts in ``__del__``. Python's cyclic collector runs on whichever
thread happens to allocate, so an abandoned cycle holding one of them can be
freed on a worker thread. tkinter then forwards the Tcl call to the Tk thread
and waits for it. If the Tk thread is itself waiting on that worker (as it
does inside MediaPipe's ``detect_async``, which waits for MediaPipe's dispatcher
thread), neither can continue and every window, including the topmost overlay,
freezes. Collecting only from the Tk event loop removes that possibility.
"""

import gc


class UiThreadGarbageCollector:
    """Disable automatic collection and run it from Tk's event loop instead.

    Every tick collects the youngest generation, which is cheap. Each
    collection advances the next generation's count, so older generations are
    collected on Python's usual ratios: with the default thresholds, a full
    collection about every 100 ticks.
    """

    INTERVAL_MS = 500

    def __init__(self, widget, *, interval_ms=INTERVAL_MS):
        self.widget = widget
        self.interval_ms = interval_ms
        self._pending = None
        self._restore = False

    def start(self):
        if self._pending is not None:
            return
        self._restore = gc.isenabled()
        gc.disable()
        self._schedule()

    def collect_due(self):
        """Collect the oldest generation past its threshold, at least the youngest."""
        counts, thresholds = gc.get_count(), gc.get_threshold()
        generation = next(
            (older for older in (2, 1) if thresholds[older] and counts[older] >= thresholds[older]), 0,
        )
        gc.collect(generation)
        return generation

    def _tick(self):
        self._pending = None
        try:
            self.collect_due()
        finally:
            self._schedule()

    def _schedule(self):
        self._pending = self.widget.after(self.interval_ms, self._tick)

    def stop(self):
        """Stop the Tk schedule and give collection back to Python."""
        if self._pending is not None:
            try:
                self.widget.after_cancel(self._pending)
            except Exception:
                pass  # The Tk interpreter may already be gone at shutdown.
            self._pending = None
        if self._restore:
            gc.enable()
            self._restore = False
