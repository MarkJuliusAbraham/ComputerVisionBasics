"""Session lifecycle races without a camera or native model runtime."""

import threading
import time
import unittest
from types import SimpleNamespace

from hand_tracking.backend.landmarker.model_loader import ModelLoader
from hand_tracking.backend.landmarker.model_status import ModelPhase


class FakeSession:
    def __init__(self, on_close=None):
        self.closed = threading.Event()
        self.close_count = 0
        self.on_close = on_close

    def close(self):
        self.close_count += 1
        if self.on_close is not None:
            self.on_close()
        self.closed.set()


class ModelLoaderTests(unittest.TestCase):
    def make_loader(self, factory):
        loader = ModelLoader(factory, SimpleNamespace(read=lambda path: path))
        self.addCleanup(loader.close)
        return loader

    def wait_for(self, predicate):
        deadline = time.monotonic() + 2.0
        pause = threading.Event()
        while time.monotonic() < deadline:
            if predicate():
                return
            pause.wait(0.001)
        self.fail("Timed out waiting for model worker")

    def ready(self, loader, path):
        loader.request(path)
        self.wait_for(lambda: loader.status.phase == ModelPhase.READY and loader.status.active_path == path)

    def test_replacement_waits_for_every_lease_without_blocking_management(self):
        first, second = FakeSession(), FakeSession()
        loader = self.make_loader({"first": first, "second": second}.__getitem__)
        self.ready(loader, "first")

        with loader.session() as outer:
            with loader.session() as inner:
                self.assertIs(outer, first)
                self.assertIs(inner, first)
                self.ready(loader, "second")
                self.assertFalse(first.closed.is_set())
                with loader.session() as current:
                    self.assertIs(current, second)
            self.assertFalse(first.closed.is_set())

        self.assertTrue(first.closed.wait(2.0))
        self.assertTrue(loader.close())
        self.assertEqual(first.close_count, 1)
        self.assertEqual(second.close_count, 1)

    def test_an_exception_releases_the_lease(self):
        session = FakeSession()
        loader = self.make_loader(lambda path: session)
        self.ready(loader, "first")

        with self.assertRaisesRegex(ValueError, "inference failed"):
            with loader.session():
                raise ValueError("inference failed")

        self.assertTrue(loader.close())
        self.assertEqual(session.close_count, 1)

    def test_shutdown_is_bounded_while_native_submission_holds_a_lease(self):
        session = FakeSession()
        loader = self.make_loader(lambda path: session)
        self.ready(loader, "first")

        with loader.session() as active:
            self.assertIs(active, session)
            started = time.monotonic()
            with self.assertLogs("hand_tracking.backend.landmarker.model_loader", level="WARNING"):
                self.assertFalse(loader.close(timeout=0.01))
            self.assertLess(time.monotonic() - started, 0.5)
            self.assertFalse(loader.status.available)
            with loader.session() as unavailable:
                self.assertIsNone(unavailable)
            self.assertFalse(session.closed.is_set())
            loader.request("ignored after shutdown")

        self.assertTrue(loader.close())
        self.assertEqual(session.close_count, 1)

    def test_shutdown_is_bounded_while_model_creation_is_blocked(self):
        loading, release = threading.Event(), threading.Event()
        session = FakeSession()

        def create(path):
            loading.set()
            release.wait(2.0)
            return session

        loader = self.make_loader(create)
        self.addCleanup(release.set)
        loader.request("blocked")
        self.assertTrue(loading.wait(2.0))
        with self.assertLogs("hand_tracking.backend.landmarker.model_loader", level="WARNING"):
            self.assertFalse(loader.close(timeout=0.01))
        self.assertFalse(loader.status.available)

        release.set()
        self.assertTrue(loader.close())
        self.assertEqual(session.close_count, 1)

    def test_shutdown_is_bounded_while_native_close_is_blocked(self):
        closing, release = threading.Event(), threading.Event()

        def close_native():
            closing.set()
            release.wait(2.0)

        session = FakeSession(close_native)
        loader = self.make_loader(lambda path: session)
        self.addCleanup(release.set)
        self.ready(loader, "first")
        with self.assertLogs("hand_tracking.backend.landmarker.model_loader", level="WARNING"):
            self.assertFalse(loader.close(timeout=0.01))
        self.assertTrue(closing.is_set())
        self.assertFalse(loader.status.available)

        release.set()
        self.assertTrue(loader.close())
        self.assertEqual(session.close_count, 1)

    def test_stale_candidate_is_closed_and_latest_request_wins(self):
        loading, release = threading.Event(), threading.Event()
        first, latest = FakeSession(), FakeSession()

        def create(path):
            if path == "first":
                loading.set()
                release.wait(2.0)
                return first
            return latest

        loader = self.make_loader(create)
        self.addCleanup(release.set)
        loader.request("first")
        self.assertTrue(loading.wait(2.0))
        loader.request("latest")
        release.set()
        self.wait_for(lambda: loader.status.active_path == "latest")

        self.assertTrue(first.closed.wait(2.0))
        with loader.session() as active:
            self.assertIs(active, latest)
        self.assertTrue(loader.close())
        self.assertEqual(first.close_count, 1)
        self.assertEqual(latest.close_count, 1)

    def test_failed_replacement_preserves_the_working_model(self):
        session = FakeSession()

        def create(path):
            if path == "broken":
                raise ValueError("Bad model\nDetails")
            return session

        loader = self.make_loader(create)
        self.ready(loader, "first")
        with self.assertLogs("hand_tracking.backend.landmarker.model_loader", level="ERROR"):
            loader.request("broken")
            self.wait_for(lambda: loader.status.phase == ModelPhase.FAILED)

        self.assertEqual(loader.status.message, "Bad model")
        self.assertEqual(loader.status.requested_path, "broken")
        self.assertEqual(loader.status.active_path, "first")
        with loader.session() as active:
            self.assertIs(active, session)
        self.assertFalse(session.closed.is_set())

    def test_clear_request_retires_the_active_session_without_loading_again(self):
        session = FakeSession()
        calls = []

        def create(path):
            calls.append(path)
            return session

        loader = self.make_loader(create)
        self.ready(loader, "first")
        with loader.session():
            loader.request("")
            self.wait_for(lambda: loader.status.phase == ModelPhase.EMPTY)
            self.assertFalse(session.closed.is_set())

        self.assertTrue(session.closed.wait(2.0))
        self.assertTrue(loader.close())
        self.assertEqual(calls, ["first"])

    def test_close_failure_is_logged_and_does_not_stop_replacement(self):
        def fail_close():
            raise RuntimeError("Native close failed")

        first, second = FakeSession(fail_close), FakeSession()
        loader = self.make_loader({"first": first, "second": second}.__getitem__)
        self.ready(loader, "first")
        with self.assertLogs("hand_tracking.backend.landmarker.model_loader", level="ERROR"):
            self.ready(loader, "second")
            self.wait_for(lambda: first.close_count == 1)
            self.assertTrue(loader.close())

        self.assertEqual(second.close_count, 1)


if __name__ == "__main__":
    unittest.main()
