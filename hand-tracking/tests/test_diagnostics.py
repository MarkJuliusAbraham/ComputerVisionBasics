"""Persistent diagnostics remain useful without cameras or a Tk main loop."""

import logging
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from hand_tracking.backend.common.diagnostics import RuntimeDiagnostics


MODULE = "hand_tracking.backend.common.diagnostics"


class RuntimeDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def test_exception_is_persisted_and_global_hooks_are_restored(self):
        previous_sys = sys.excepthook
        previous_thread = threading.excepthook
        root = logging.getLogger()
        previous_level = root.level
        previous_handlers = root.handlers[:]
        with self.assertRaisesRegex(RuntimeError, "synthetic application failure"):
            with RuntimeDiagnostics(self.directory):
                raise RuntimeError("synthetic application failure")
        self.assertIs(sys.excepthook, previous_sys)
        self.assertIs(threading.excepthook, previous_thread)
        self.assertEqual(root.level, previous_level)
        self.assertEqual(root.handlers, previous_handlers)
        output = (self.directory / "application.log").read_text(encoding="utf-8")
        self.assertIn("Application exited unexpectedly", output)
        self.assertIn("synthetic application failure", output)
        self.assertIn("PID ", output)
        self.assertIn("UI thread 0x", output)

    def test_unhandled_exception_hooks_persist_errors_and_chain_previous_hooks(self):
        previous_sys = Mock()
        previous_thread = Mock()
        error = ValueError("synthetic worker failure")
        args = SimpleNamespace(
            exc_type=ValueError, exc_value=error, exc_traceback=None,
            thread=SimpleNamespace(name="model-loader"),
        )
        with patch.object(sys, "excepthook", previous_sys), patch.object(threading, "excepthook", previous_thread):
            with RuntimeDiagnostics(self.directory):
                sys.excepthook(ValueError, error, None)
                threading.excepthook(args)
            self.assertIs(sys.excepthook, previous_sys)
            self.assertIs(threading.excepthook, previous_thread)
        previous_sys.assert_called_once_with(ValueError, error, None)
        previous_thread.assert_called_once_with(args)
        output = (self.directory / "application.log").read_text(encoding="utf-8")
        self.assertIn("Unhandled main-thread exception", output)
        self.assertIn("Unhandled exception in thread model-loader", output)

    def test_watchdog_arms_on_progress_and_dumps_once_until_progress_resumes(self):
        now = [0.0]
        diagnostics = RuntimeDiagnostics(self.directory, stall_timeout_seconds=10, clock=lambda: now[0])
        with patch(f"{MODULE}.faulthandler.dump_traceback") as dump:
            with diagnostics:
                now[0] = 100
                diagnostics._check_heartbeat()
                dump.assert_not_called()  # Startup or an idle, unused runtime is not a stall.
                diagnostics.heartbeat()
                now[0] = 109
                diagnostics._check_heartbeat()
                dump.assert_not_called()
                now[0] = 110
                diagnostics._check_heartbeat()
                diagnostics._check_heartbeat()
                dump.assert_called_once()
                diagnostics.heartbeat()
                now[0] = 121
                diagnostics._check_heartbeat()
                self.assertEqual(dump.call_count, 2)
        output = (self.directory / "application.log").read_text(encoding="utf-8")
        self.assertEqual(output.count("UI heartbeat stalled"), 2)
        self.assertIn("UI heartbeat resumed", output)
        self.assertEqual((self.directory / "thread-dumps.log").read_text().count("UI heartbeat stalled"), 2)

    def test_watchdog_writes_real_thread_stacks_and_stops_on_exit(self):
        now = [0.0]
        diagnostics = RuntimeDiagnostics(self.directory, stall_timeout_seconds=1, clock=lambda: now[0])
        with diagnostics:
            thread = diagnostics._watchdog
            diagnostics.heartbeat()
            now[0] = 2
            diagnostics._check_heartbeat()
        self.assertFalse(thread.is_alive())
        output = (self.directory / "thread-dumps.log").read_text(encoding="utf-8")
        self.assertIn("test_watchdog_writes_real_thread_stacks", output)
        self.assertIn("PID ", output)
        diagnostics.close()  # Repeated shutdown is harmless.

    def test_failed_watchdog_start_restores_hooks_and_closes_files(self):
        previous_sys = sys.excepthook
        previous_thread = threading.excepthook
        diagnostics = RuntimeDiagnostics(self.directory)
        with patch(f"{MODULE}.threading.Thread.start", side_effect=RuntimeError("cannot start thread")):
            with self.assertRaisesRegex(RuntimeError, "cannot start thread"):
                with diagnostics:
                    pass
        self.assertIs(sys.excepthook, previous_sys)
        self.assertIs(threading.excepthook, previous_thread)
        self.assertIsNone(diagnostics._dump_file)
        self.assertIsNone(diagnostics._handler)

    def test_stuck_watchdog_detaches_logging_without_touching_its_locked_files(self):
        diagnostics = RuntimeDiagnostics(self.directory)
        root = logging.getLogger()
        previous_level = root.level
        previous_sys = sys.excepthook
        previous_thread = threading.excepthook
        self.addCleanup(setattr, sys, "excepthook", previous_sys)
        self.addCleanup(setattr, threading, "excepthook", previous_thread)
        self.addCleanup(root.setLevel, previous_level)
        watchdog = Mock(ident=123)
        watchdog.is_alive.return_value = True
        handler = Mock()
        dump_file = Mock()
        diagnostics._watchdog = watchdog
        diagnostics._handler = handler
        diagnostics._dump_file = dump_file
        diagnostics._previous_log_level = previous_level
        diagnostics._previous_sys_hook = previous_sys
        diagnostics._previous_thread_hook = previous_thread
        sys.excepthook = diagnostics._report_exception
        threading.excepthook = diagnostics._report_thread_exception
        root.addHandler(handler)
        self.addCleanup(root.removeHandler, handler)
        root.setLevel(logging.INFO)

        with patch(f"{MODULE}.LOGGER") as logger:
            diagnostics.close()

        watchdog.join.assert_called_once_with(timeout=1.0)
        self.assertNotIn(handler, root.handlers)
        handler.close.assert_not_called()
        dump_file.close.assert_not_called()
        self.assertEqual(logger.mock_calls, [])
        self.assertIs(sys.excepthook, previous_sys)
        self.assertIs(threading.excepthook, previous_thread)
        self.assertEqual(root.level, previous_level)

    def test_existing_faulthandler_owner_is_preserved(self):
        with patch(f"{MODULE}.faulthandler.is_enabled", return_value=True):
            with patch(f"{MODULE}.faulthandler.enable") as enable, patch(f"{MODULE}.faulthandler.disable") as disable:
                with RuntimeDiagnostics(self.directory):
                    pass
            enable.assert_not_called()
            disable.assert_not_called()

    def test_owned_faulthandler_is_disabled_before_its_file_is_closed(self):
        with patch(f"{MODULE}.faulthandler.is_enabled", return_value=False):
            with patch(f"{MODULE}.faulthandler.enable") as enable, patch(f"{MODULE}.faulthandler.disable") as disable:
                diagnostics = RuntimeDiagnostics(self.directory)
                with diagnostics:
                    dump_file = diagnostics._dump_file
                    disable.side_effect = lambda: self.assertFalse(dump_file.closed)
                enable.assert_called_once_with(file=dump_file, all_threads=True)
                disable.assert_called_once()
                self.assertTrue(dump_file.closed)

    def test_unwritable_diagnostics_do_not_prevent_application_startup(self):
        # A file in the place of a directory fails consistently on every OS.
        path = self.directory / "file"
        path.write_text("occupied", encoding="utf-8")
        with self.assertLogs(MODULE, level="WARNING"):
            with RuntimeDiagnostics(path) as diagnostics:
                diagnostics.heartbeat()

    def test_later_exception_hook_owner_is_not_overwritten_on_close(self):
        original = sys.excepthook
        self.addCleanup(setattr, sys, "excepthook", original)
        other_owner = Mock()
        with RuntimeDiagnostics(self.directory):
            sys.excepthook = other_owner
        self.assertIs(sys.excepthook, other_owner)

    def test_invalid_timeout_is_rejected(self):
        for timeout in (0, -1, float("inf"), float("nan")):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                RuntimeDiagnostics(self.directory, stall_timeout_seconds=timeout)


if __name__ == "__main__":
    unittest.main()
