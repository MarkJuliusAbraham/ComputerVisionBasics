"""The engine thread: request ordering, publishing, shutdown, and failures."""

import threading
import time
import unittest
from types import SimpleNamespace

import numpy as np

from hand_tracking.backend.capture.camera import Camera
from hand_tracking.backend.engine.engine import TrackingSwitches
from hand_tracking.backend.engine.runner import EngineRunner


class FakeEngine:
    """Records what happens, in order; each frame returns a result unless told otherwise."""

    def __init__(self) -> None:
        self.switches = TrackingSwitches()
        self.events = []
        self.frames = 0
        self.fail_on_frame = None
        self.produce_results = True

    def process_frame(self, *, preview_requested, wait_seconds):
        self.frames += 1
        self.events.append(("frame", preview_requested))
        if self.frames == self.fail_on_frame:
            raise RuntimeError("inference failed")
        time.sleep(0.001)
        return SimpleNamespace(frame=None) if self.produce_results else None

    def finish_frame(self):
        pass


def wait_until(condition, timeout=2.0):
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError("timed out")
        time.sleep(0.001)


class EngineRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = FakeEngine()
        self.runner = EngineRunner(self.engine)
        self.addCleanup(self.runner.stop)

    def test_requests_run_in_order_before_the_next_frame(self) -> None:
        self.runner.submit(lambda engine: engine.events.append("pause"))
        self.runner.submit(lambda engine: engine.events.append("commands off"))
        self.runner.start()
        wait_until(lambda: self.engine.frames >= 2)
        self.assertEqual(self.engine.events[:3], ["pause", "commands off", ("frame", False)])

    def test_a_request_made_while_running_affects_the_next_frame(self) -> None:
        self.runner.start()
        wait_until(lambda: self.engine.frames >= 1)
        self.runner.submit(lambda engine: engine.events.append("commands off"))
        wait_until(lambda: "commands off" in self.engine.events and self.engine.events[-1] != "commands off")
        after = self.engine.events[self.engine.events.index("commands off") + 1]
        self.assertEqual(after[0], "frame")

    def test_preview_requests_reach_the_engine(self) -> None:
        self.runner.set_preview_requested(True)
        self.runner.start()
        wait_until(lambda: self.engine.frames >= 1)
        self.assertEqual(self.engine.events[0], ("frame", True))

    def test_results_are_published_with_increasing_sequence(self) -> None:
        self.runner.start()
        wait_until(lambda: self.runner.snapshot().sequence >= 3)
        first = self.runner.snapshot()
        wait_until(lambda: self.runner.snapshot().sequence > first.sequence)
        self.assertIsNotNone(self.runner.snapshot().result)
        self.assertIsNot(self.runner.snapshot().switches, self.engine.switches)  # A copy

    def test_nothing_new_publishes_nothing(self) -> None:
        self.engine.produce_results = False
        self.runner.start()
        wait_until(lambda: self.engine.frames >= 5)
        self.assertEqual(self.runner.snapshot().sequence, 0)

    def test_stop_still_applies_pending_requests(self) -> None:
        self.runner.start()
        wait_until(lambda: self.engine.frames >= 1)
        self.runner.submit(lambda engine: engine.events.append("commands off"))
        self.runner.stop()
        self.assertIn("commands off", self.engine.events)
        self.assertFalse(self.runner._thread.is_alive())

    def test_engine_failure_is_kept_for_the_ui_and_ends_the_thread(self) -> None:
        self.engine.fail_on_frame = 2
        with self.assertLogs("hand_tracking.backend.engine.runner", "ERROR"):
            self.runner.start()
            wait_until(lambda: self.runner.failure is not None)
        self.runner._thread.join(1)
        self.assertFalse(self.runner._thread.is_alive())
        self.assertEqual(str(self.runner.failure), "inference failed")


class CameraNewerFrameTests(unittest.TestCase):
    """read_newer, without opening a device."""

    def setUp(self) -> None:
        self.camera = Camera.__new__(Camera)
        self.camera._lock = threading.Lock()
        self.camera._new_frame = threading.Condition(self.camera._lock)
        self.camera._frame = None
        self.camera._sequence = 0

    def publish(self, value) -> None:
        with self.camera._new_frame:
            self.camera._frame = np.full((2, 2, 3), value, np.uint8)
            self.camera._sequence += 1
            self.camera._new_frame.notify_all()

    def test_nothing_newer_returns_no_frame_and_the_same_sequence(self) -> None:
        self.publish(1)
        frame, sequence = self.camera.read_newer(0, timeout=0)
        self.assertIsNotNone(frame)
        self.assertEqual(self.camera.read_newer(sequence, timeout=0.01), (None, sequence))

    def test_waits_for_a_newer_frame_and_returns_a_copy(self) -> None:
        threading.Timer(0.02, self.publish, args=(7,)).start()
        frame, sequence = self.camera.read_newer(0, timeout=1)
        self.assertEqual((sequence, int(frame[0, 0, 0])), (1, 7))
        frame[:] = 0
        self.assertEqual(int(self.camera._frame[0, 0, 0]), 7)


if __name__ == "__main__":
    unittest.main()
