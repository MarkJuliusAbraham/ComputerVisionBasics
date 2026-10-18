"""Fail-closed frame processing and shutdown ordering without native windows."""

import unittest
from unittest.mock import Mock

from hand_tracking.frontend.application import Application


class ApplicationLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.app = Application.__new__(Application)
        self.app.running = True
        self.app._closed = False
        self.app._failed = False
        self.app._heartbeat = Mock()
        self.app.engine = Mock()
        self.app.preview = Mock()
        self.app.gui = Mock()
        self.app._process_frame_work = Mock(return_value=1)
        self.events = Mock()
        self.events.attach_mock(self.app.gui.hide_overlays, "hide")
        self.events.attach_mock(self.app.engine.set_commands_active, "commands")
        self.events.attach_mock(self.app.gui.show_failure, "report")
        self.events.attach_mock(self.app.gui.quit, "quit")
        self.events.attach_mock(self.app.engine.close, "engine_close")
        self.events.attach_mock(self.app.gui.close, "windows_close")
        self.events.attach_mock(self.app.preview.close, "preview_close")

    def event_names(self):
        return [call[0] for call in self.events.mock_calls]

    def test_success_schedules_only_after_frame_and_profiler_complete(self):
        self.app._process_frame()
        self.app.engine.finish_frame.assert_called_once()
        self.app.gui.after.assert_called_once_with(1, self.app._process_frame)
        self.app.gui.quit.assert_not_called()

    def test_heartbeat_continues_in_error_dialog_but_stops_after_close(self):
        self.app.running = False
        self.app._poll_ui_heartbeat()
        self.app._heartbeat.assert_called_once()
        self.app.gui.after.assert_called_once_with(1000, self.app._poll_ui_heartbeat)
        self.app._closed = True
        self.app._poll_ui_heartbeat()
        self.app._heartbeat.assert_called_once()

    def test_failed_frame_stops_input_hides_overlay_and_never_schedules_again(self):
        self.app._process_frame_work.side_effect = RuntimeError("inference failed")
        with self.assertLogs("hand_tracking.frontend.application", "ERROR"):
            self.app._process_frame()
        self.assertFalse(self.app.running)
        self.app.engine.finish_frame.assert_called_once()
        self.app.gui.after.assert_not_called()
        self.assertEqual(self.event_names(), ["hide", "commands", "report", "quit"])
        self.app.engine.set_commands_active.assert_called_once_with(False)
        self.app.gui.show_failure.assert_called_once_with("inference failed")
        self.app._process_frame()
        self.assertEqual(self.app._process_frame_work.call_count, 1)

    def test_profiler_failure_also_stops_the_loop(self):
        self.app.engine.finish_frame.side_effect = ValueError("profiler failed")
        with self.assertLogs("hand_tracking.frontend.application", "ERROR"):
            self.app._process_frame()
        self.app.gui.after.assert_not_called()
        self.assertFalse(self.app.running)

    def test_failure_cleanup_continues_when_hiding_and_error_dialog_fail(self):
        self.app._process_frame_work.side_effect = RuntimeError("frame failed")
        self.app.gui.hide_overlays.side_effect = RuntimeError("hide failed")
        self.app.gui.show_failure.side_effect = RuntimeError("dialog failed")
        with self.assertLogs("hand_tracking.frontend.application", "ERROR"):
            self.app._process_frame()
        self.app.engine.set_commands_active.assert_called_once_with(False)
        self.app.gui.quit.assert_called_once()

    def test_quit_still_exits_when_overlay_hiding_fails(self):
        self.app.gui.hide_overlays.side_effect = RuntimeError("hide failed")
        with self.assertLogs("hand_tracking.frontend.application", "ERROR"):
            self.app.request_quit()
        self.app.gui.quit.assert_called_once()

    def test_shutdown_hides_before_native_cleanup_and_is_idempotent(self):
        self.app.close()
        self.app.close()
        self.assertEqual(self.event_names(), ["hide", "engine_close", "windows_close", "preview_close"])

    def test_shutdown_attempts_windows_and_preview_even_if_engine_close_raises(self):
        self.app.engine.close.side_effect = RuntimeError("engine failed")
        with self.assertRaisesRegex(RuntimeError, "engine failed"):
            self.app.close()
        self.assertEqual(self.event_names(), ["hide", "engine_close", "windows_close", "preview_close"])


if __name__ == "__main__":
    unittest.main()
