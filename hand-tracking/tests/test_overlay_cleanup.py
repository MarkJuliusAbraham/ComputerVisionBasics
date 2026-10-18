"""Failure-injection checks for overlay and window ownership, without a GUI."""

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from hand_tracking.frontend.components.overlays.window import ClickThroughOverlayWindow
from hand_tracking.frontend.control_window import ControlWindow
from hand_tracking.frontend.tracking.hand.module import HandTrackingModule
from hand_tracking.frontend.tracking.hand.overlay.hand_tracking_overlay import HandTrackingOverlay
from hand_tracking.frontend.tracking.hand.overlay.options_dialog import OverlayOptionsDialog
from hand_tracking.frontend.tracking.registry import TrackingWindowRegistry


class OverlayCleanupTests(unittest.TestCase):
    def test_failed_hub_construction_destroys_the_partial_tk_root(self):
        root = Mock()
        context = SimpleNamespace(callbacks=SimpleNamespace(on_close=Mock()))
        with patch("hand_tracking.frontend.control_window.tk.Tk", return_value=root), patch(
            "hand_tracking.frontend.control_window.WindowShell",
            side_effect=RuntimeError("shell failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "shell failed"):
                ControlWindow(context)
        root.destroy.assert_called_once()

    def make_window(self):
        events = []
        window = ClickThroughOverlayWindow.__new__(ClickThroughOverlayWindow)
        window._closed = window._destroyed = window._presenter_closed = False
        window.window = SimpleNamespace(
            withdraw=Mock(side_effect=lambda: events.append("hide")),
            destroy=Mock(side_effect=lambda: events.append("destroy")),
        )
        window._presenter = SimpleNamespace(
            close=Mock(side_effect=lambda: events.append("presenter")),
        )
        return window, events

    def test_presenter_failure_cannot_leave_visible_window_and_can_retry(self):
        window, events = self.make_window()

        def fail_presenter():
            events.append("presenter")
            raise RuntimeError("graphics cleanup failed")

        window._presenter.close.side_effect = fail_presenter
        with self.assertRaisesRegex(RuntimeError, "graphics cleanup"):
            window.close()
        self.assertEqual(events, ["hide", "destroy", "presenter"])

        window._presenter.close.side_effect = lambda: events.append("presenter retry")
        window.close()
        window.close()
        window.show()
        self.assertEqual(events, ["hide", "destroy", "presenter", "presenter retry"])

    def test_failed_hide_still_destroys_window_and_releases_presenter(self):
        window, events = self.make_window()
        window.window.withdraw.side_effect = RuntimeError("withdraw failed")
        with self.assertRaisesRegex(RuntimeError, "withdraw"):
            window.close()
        self.assertEqual(events, ["destroy", "presenter"])

    def test_failed_destruction_is_retryable_without_releasing_presenter_twice(self):
        window, events = self.make_window()
        window.window.destroy.side_effect = RuntimeError("destroy failed")
        with self.assertRaisesRegex(RuntimeError, "destroy"):
            window.close()
        window.window.destroy.side_effect = lambda: events.append("destroy retry")
        window.close()
        self.assertEqual(events, ["hide", "presenter", "hide", "destroy retry"])
        window._presenter.close.assert_called_once()

    def test_shutdown_closes_overlay_when_options_destruction_fails(self):
        events = []
        overlay = HandTrackingOverlay(None, max_deviation=10)
        overlay._window = SimpleNamespace(
            hide=lambda: events.append("hide"), close=lambda: events.append("close"),
        )
        overlay._options = SimpleNamespace(
            destroy=Mock(side_effect=RuntimeError("options failed")),
            set_enabled=lambda enabled: events.append(("enabled", enabled)),
        )
        with self.assertRaisesRegex(RuntimeError, "options"):
            overlay.shutdown()
        self.assertEqual(events, ["hide", "close", ("enabled", False)])
        self.assertFalse(overlay.enabled)

    def test_options_window_destroyed_even_when_reposition_callback_fails(self):
        options = OverlayOptionsDialog.__new__(OverlayOptionsDialog)
        options._set_repositioning = Mock(side_effect=RuntimeError("reposition failed"))
        options.window = SimpleNamespace(destroy=Mock())
        options._on_close = Mock()
        with self.assertRaisesRegex(RuntimeError, "reposition"):
            options.destroy()
        options.window.destroy.assert_called_once()
        options._on_close.assert_called_once()

    def test_hand_workspace_destroyed_when_overlay_shutdown_fails(self):
        module = HandTrackingModule.__new__(HandTrackingModule)
        module._debug_active = True
        module.overlay = SimpleNamespace(shutdown=Mock(side_effect=RuntimeError("overlay failed")))
        close_window = Mock()
        module.window = SimpleNamespace(close=close_window)
        with self.assertRaisesRegex(RuntimeError, "overlay"):
            module.close()
        close_window.assert_called_once()
        self.assertIsNone(module.window)
        self.assertFalse(module._debug_active)

    def test_registry_attempts_every_hide_and_close_after_a_failure(self):
        events = []

        def fail_hide():
            events.append("hide first")
            raise RuntimeError("hide failed")

        def fail_close():
            events.append("close first")
            raise RuntimeError("close failed")

        registry = TrackingWindowRegistry((
            SimpleNamespace(key="first", hide_overlays=fail_hide, close=fail_close),
            SimpleNamespace(
                key="second", hide_overlays=lambda: events.append("hide second"),
                close=lambda: events.append("close second"),
            ),
        ))
        with self.assertRaisesRegex(RuntimeError, "close"):
            registry.close()
        self.assertEqual(events, ["hide first", "hide second", "close first", "close second"])

    def test_control_root_destroyed_when_module_cleanup_fails(self):
        gui = ControlWindow.__new__(ControlWindow)
        gui.context = SimpleNamespace(tracking_modules=SimpleNamespace(
            close=Mock(side_effect=RuntimeError("modules failed")),
        ))
        gui.shell = SimpleNamespace(view=SimpleNamespace(root=SimpleNamespace(destroy=Mock())))
        with self.assertRaisesRegex(RuntimeError, "modules"):
            gui.close()
        gui.shell.view.root.destroy.assert_called_once()

    def test_unhandled_callback_logs_and_requests_shutdown(self):
        gui = ControlWindow.__new__(ControlWindow)
        gui._on_quit = Mock()
        gui.show_failure = Mock()
        error = RuntimeError("callback failed")
        with self.assertLogs("hand_tracking.frontend.control_window", level="ERROR") as output:
            gui._report_callback_exception(RuntimeError, error, None)
        self.assertIn("callback failed", "\n".join(output.output))
        gui._on_quit.assert_called_once()
        gui.show_failure.assert_called_once_with("callback failed")


if __name__ == "__main__":
    unittest.main()
