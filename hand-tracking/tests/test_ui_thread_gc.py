"""Cyclic garbage is finalized only on the thread that runs the Tk event loop."""

import gc
import threading
import unittest

from hand_tracking.frontend.core.ui_thread_gc import UiThreadGarbageCollector


class FakeEventLoop:
    """Record scheduled callbacks instead of running a Tk event loop."""

    def __init__(self) -> None:
        self.callbacks = {}
        self._next = 0

    def after(self, _delay_ms, callback):
        self._next += 1
        self.callbacks[self._next] = callback
        return self._next

    def after_cancel(self, identifier):
        self.callbacks.pop(identifier, None)

    def run_pending(self):
        for identifier, callback in list(self.callbacks.items()):
            del self.callbacks[identifier]
            callback()


class FinalizedOnThread:
    """Stands in for a tkinter Font: a cycle whose __del__ records its thread."""

    def __init__(self, record) -> None:
        self.record = record
        self.cycle = self

    def __del__(self) -> None:
        self.record.append(threading.get_ident())


class UiThreadGarbageCollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(gc.enable if gc.isenabled() else gc.disable)
        gc.enable()
        gc.collect()

    def test_worker_allocations_never_finalize_tk_objects(self) -> None:
        loop = FakeEventLoop()
        collector = UiThreadGarbageCollector(loop)
        collector.start()
        self.addCleanup(collector.stop)

        finalized_on = []
        FinalizedOnThread(finalized_on)  # Abandoned at once; only the cyclic collector frees it.

        def allocate_like_mediapipe():
            for _ in range(50_000):
                [[], {}]  # Container allocations normally trigger automatic collection.

        worker = threading.Thread(target=allocate_like_mediapipe)
        worker.start()
        worker.join()
        self.assertEqual(finalized_on, [], "a worker thread finalized the object")

        loop.run_pending()
        self.assertEqual(finalized_on, [threading.get_ident()])

    def test_stop_restores_automatic_collection(self) -> None:
        loop = FakeEventLoop()
        collector = UiThreadGarbageCollector(loop)
        collector.start()
        self.assertFalse(gc.isenabled())
        collector.stop()
        self.assertTrue(gc.isenabled())
        self.assertEqual(loop.callbacks, {})


if __name__ == "__main__":
    unittest.main()
