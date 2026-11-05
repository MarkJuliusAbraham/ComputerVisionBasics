"""Fail-closed polling of the engine thread and shutdown ordering without native windows."""

import unittest
from unittest.mock import MagicMock, Mock

from hand_tracking.frontend.application import HEARTBEAT_INTERVAL_MS, POLL_INTERVAL_MS, Application


class ApplicationLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.app = Application.__new__(Application)
        self.app.running = True
        self.app._closed = False
        self.app._failed = False
        self.app._heartbeat = Mock()
        self.app.runner = Mock(failure=None)
        self.app.engine = MagicMock()
        self.app.preview = Mock()
        self.app.gui = Mock()
        self.app.hand_tracking = Mock(preview_active=False)
        self.app._garbage_collector = Mock()
        self.app._display = Mock()
        self.events = Mock()
        self.events.attach_mock(self.app.gui.hide_overlays, "hide")
        self.events.attach_mock(self.app.engine.set_commands_active, "commands")
        self.events.attach_mock(self.app.runner.submit, "request")
        self.events.attach_mock(self.app.gui.show_failure, "report")
        self.events.attach_mock(self.app.gui.quit, "quit")
        self.events.attach_mock(self.app.runner.stop, "engine_stop")
        self.events.attach_mock(self.app.engine.close, "engine_close")
        self.events.attach_mock(self.app.gui.close, "windows_close")
        self.events.attach_mock(self.app.preview.close, "preview_close")

    def event_names(self):
        return [call[0] for call in self.events.mock_calls]

    def test_poll_displays_the_latest_snapshot_and_polls_again(self):
        self.app._poll_engine()
        self.app._display.assert_called_once_with(self.app.runner.snapshot.return_value)
        self.app.runner.set_preview_requested.assert_called_once_with(False)
        self.app.gui.after.assert_called_once_with(POLL_INTERVAL_MS, self.app._poll_engine)
        self.app.gui.quit.assert_not_called()

    def test_heartbeat_continues_in_error_dialog_but_stops_after_close(self):
        self.app.running = False
        self.app._poll_ui_heartbeat()
        self.app._heartbeat.assert_called_once()
        self.app.gui.after.assert_called_once_with(HEARTBEAT_INTERVAL_MS, self.app._poll_ui_heartbeat)
        self.app._closed = True
        self.app._poll_ui_heartbeat()
        self.app._heartbeat.assert_called_once()

    def test_engine_thread_failure_stops_input_hides_overlay_and_never_polls_again(self):
        self.app.runner.failure = RuntimeError("inference failed")
        with self.assertLogs("hand_tracking.frontend.application", "ERROR"):
            self.app._poll_engine()
        self.assertFalse(self.app.running)
        self.app.gui.after.assert_not_called()
        # The engine thread has ended, so commands are stopped directly.
        self.assertEqual(self.event_names(), ["hide", "commands", "report", "quit"])
        self.app.engine.set_commands_active.assert_called_once_with(False)
        self.app.gui.show_failure.assert_called_once_with("inference failed")
        self.app._poll_engine()
        self.app._display.assert_not_called()

    def test_display_failure_asks_the_running_engine_to_stop_commands(self):
        self.app._display.side_effect = RuntimeError("display failed")
        with self.assertLogs("hand_tracking.frontend.application", "ERROR"):
            self.app._poll_engine()
        self.assertEqual(self.event_names(), ["hide", "request", "report", "quit"])
        self.app.engine.set_commands_active.assert_not_called()

    def test_failure_cleanup_continues_when_hiding_and_error_dialog_fail(self):
        self.app.runner.failure = RuntimeError("frame failed")
        self.app.gui.hide_overlays.side_effect = RuntimeError("hide failed")
        self.app.gui.show_failure.side_effect = RuntimeError("dialog failed")
        with self.assertLogs("hand_tracking.frontend.application", "ERROR"):
            self.app._poll_engine()
        self.app.engine.set_commands_active.assert_called_once_with(False)
        self.app.gui.quit.assert_called_once()

    def test_quit_still_exits_when_overlay_hiding_fails(self):
        self.app.gui.hide_overlays.side_effect = RuntimeError("hide failed")
        with self.assertLogs("hand_tracking.frontend.application", "ERROR"):
            self.app.request_quit()
        self.app.gui.quit.assert_called_once()

    def test_shutdown_stops_the_engine_thread_before_releasing_input_and_is_idempotent(self):
        self.app.close()
        self.app.close()
        self.assertEqual(
            self.event_names(),
            ["hide", "engine_stop", "engine_close", "windows_close", "preview_close"],
        )
        self.app._garbage_collector.stop.assert_called_once()

    def test_shutdown_attempts_windows_and_preview_even_if_engine_close_raises(self):
        self.app.engine.close.side_effect = RuntimeError("engine failed")
        with self.assertRaisesRegex(RuntimeError, "engine failed"):
            self.app.close()
        self.assertEqual(
            self.event_names(),
            ["hide", "engine_stop", "engine_close", "windows_close", "preview_close"],
        )


if __name__ == "__main__":
    unittest.main()
