import time
import logging
from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass

from hand_tracking.backend.engine.engine import FrameResult, TrackingEngine
from hand_tracking.backend.engine.runner import EngineRunner, EngineSnapshot
from hand_tracking.backend.settings.settings_manager import SettingsData, SettingsValues
from hand_tracking.frontend.control_window import ControlWindow as Gui
from hand_tracking.frontend.core.state import ControlCallbacks, ControlWindowContext, PanelSet
from hand_tracking.frontend.core.ui_thread_gc import UiThreadGarbageCollector
from hand_tracking.frontend.main_panel.main_panel import MainPanel
from hand_tracking.frontend.platforms.base import FramePreview, Platform
from hand_tracking.frontend.settings_panel.settings_panel import SettingsPanel
from hand_tracking.frontend.tracking.registry import TrackingWindowRegistry
from hand_tracking.frontend.tracking.hand.module import HandTrackingActions, HandTrackingModule

logger = logging.getLogger(__name__)

# How often the UI picks up the engine's latest result: faster than the camera.
POLL_INTERVAL_MS = 15


@dataclass
class DisplayThrottle:
    """Refresh immediately on a change; otherwise at most once per interval."""

    interval_seconds: float = 0.1
    snapshot: object = None
    updated_at: float = 0.0

    def invalidate(self) -> None:
        self.snapshot = None

    def reset(self) -> None:
        self.snapshot = None
        self.updated_at = 0.0

    def due(self, snapshot, now) -> bool:
        return snapshot != self.snapshot or now - self.updated_at >= self.interval_seconds

    def mark(self, snapshot, now) -> None:
        self.snapshot = snapshot
        self.updated_at = now


class Application:
    """Runs the control windows and displays what the tracking engine produces.

    The engine runs on its own thread (``EngineRunner``). This class only sends
    it requests and displays its latest snapshot, so a busy UI never delays
    tracking or keyboard commands, and tracking never delays a click.
    """

    def __init__(
        self, runner: EngineRunner, preview: FramePreview, *,
        heartbeat: Callable[[], None] | None = None, platform: Platform | None = None,
    ):
        platform = platform if platform is not None else Platform()
        self.runner = runner
        self.engine = runner.engine
        self.preview = preview
        self._heartbeat = heartbeat
        self._closed = False
        self._failed = False
        settings = self.engine.settings

        self.running = True
        self.restart_requested = False
        self._paused = False
        self._seen_sequence = 0
        self._switches = runner.snapshot().switches
        self._camera_ui_state = None
        self._model_ui_state = None
        self._gesture_display = DisplayThrottle()
        self._hand_reports = []
        self._preview_hidden = False
        self.hand_tracking = HandTrackingModule(
            settings, HandTrackingActions(
                restart=self.restart_hand_tracking,
                toggle_pause=self.toggle_tracking,
                activity_changed=self.set_tracking_tab_active,
                apply_settings=self.apply_changes,
                apply_mapping=self.apply_gesture_config,
            ),
            model_asset=self.engine.model_asset, platform=platform,
        )
        tracking_modules = TrackingWindowRegistry((self.hand_tracking,))
        panels = PanelSet(main=MainPanel(tracking_modules), settings=SettingsPanel())
        self.panels = panels
        camera = self.engine.camera
        callbacks = ControlCallbacks(
            on_restart=self.request_restart,
            on_close=self.request_quit,
            on_settings_path=self.load_settings_file,
            on_apply=self.apply_changes,
            on_camera_switch=camera.request_switch,  # Thread-safe: the camera queues it
        )
        context = ControlWindowContext(
            settings=settings,
            callbacks=callbacks,
            panels=panels,
            camera_index=camera.requested_index,
            tracking_modules=tracking_modules,
            platform=platform,
        )
        self.gui = Gui(context)
        self.preview.attach(self.gui.window_parent)
        self._garbage_collector = UiThreadGarbageCollector(self.gui)

    # Requests to the engine ----------------------------------------------------

    def load_settings_file(self, path: str) -> bool:
        """Called when the user browses to a different file."""
        if not self.gui.confirm_pending_changes():
            return False
        settings = self.engine.settings
        settings.use_file(path)
        self.runner.submit(TrackingEngine.apply_settings)
        self.gui.apply_display(settings.data)
        self.panels.settings.show_settings(settings)
        self.hand_tracking.reload_settings(settings)
        self._invalidate_gesture_display()
        return True

    def apply_changes(self, values: SettingsValues) -> SettingsData:
        """Apply only the fields owned by the settings panel that submitted them."""
        # Validate and save here so a rejected value is reported immediately.
        data = self.engine.save_changes(values)
        self.runner.submit(TrackingEngine.apply_settings)
        settings = self.engine.settings
        self.gui.apply_display(data)
        self.panels.settings.rebase(settings, values)
        self.hand_tracking.synchronize(settings, values)
        self._invalidate_gesture_display()
        return data

    def apply_gesture_config(self, config) -> None:
        self.runner.submit(lambda engine: engine.apply_gesture_config(config))

    def request_restart(self) -> None:
        if not self.running:
            return
        self.engine.restart_camera()  # Thread-safe: the camera queues it
        self._camera_ui_state = None
        self.restart_hand_tracking()

    def restart_hand_tracking(self) -> None:
        """Reset the hand pipeline without rebuilding windows or the shared camera."""
        if not self.running:
            return
        self.runner.submit(TrackingEngine.restart_hand_tracking)
        self._paused = False
        self._hand_reports = []
        self._gesture_display.reset()
        self.hand_tracking.set_tracking_paused(False)

    def request_quit(self) -> None:
        self.running = False
        try:
            self.gui.hide_overlays()
        except Exception:
            logger.exception("Could not hide overlays while quitting")
        try:
            self._stop_commands()
        except Exception:
            logger.exception("Could not cancel gesture commands while quitting")
        self.gui.quit()

    def toggle_tracking(self) -> None:
        paused = self._paused = not self._paused
        self.runner.submit(lambda engine: engine.set_paused(paused))
        self.hand_tracking.set_tracking_paused(paused)

    def set_tracking_tab_active(self, active: bool) -> None:
        """The hand debugging page or enabled overlay can keep commands active."""
        self.runner.submit(lambda engine: engine.set_commands_active(active))
        if not active:
            self._hand_reports = []
        self._invalidate_gesture_display()

    def _stop_commands(self) -> None:
        if self.runner.failure is not None:
            # The engine thread has ended, so the engine can be used directly.
            self.engine.set_commands_active(False)
        else:
            self.runner.submit(lambda engine: engine.set_commands_active(False))

    def _invalidate_gesture_display(self) -> None:
        self._gesture_display.invalidate()

    # The UI loop -------------------------------------------------------------

    def run(self):
        try:
            # Free tkinter objects only on this thread; see ui_thread_gc.py.
            self._garbage_collector.start()
            self.runner.start()
            self._poll_ui_heartbeat()
            self.gui.after(0, self._poll_engine)
            self.gui.run()
        except KeyboardInterrupt:
            self.running = False
        finally:
            self.close()

    def _poll_ui_heartbeat(self) -> None:
        """Measure UI responsiveness, including time spent in a modal error dialog."""
        if not self._closed and self._heartbeat is not None:
            self._heartbeat()
            self.gui.after(1000, self._poll_ui_heartbeat)

    def _poll_engine(self):
        """Display the engine's newest result, then yield to the event loop."""
        if not self.running:
            return
        try:
            failure = self.runner.failure
            if failure is not None:
                raise failure
            self.runner.set_preview_requested(self.hand_tracking.preview_active)
            self._display(self.runner.snapshot())
            if self.running:
                self.gui.after(POLL_INTERVAL_MS, self._poll_engine)
        except KeyboardInterrupt:
            self.request_quit()
        except Exception as error:
            self._stop_on_failure(error)

    def _stop_on_failure(self, error: BaseException) -> None:
        """Stop commands and remove topmost surfaces before reporting a fatal error."""
        if self._failed:
            return
        self._failed = True
        self.running = False
        for description, action in (
            ("hide overlays", self.gui.hide_overlays),
            ("stop gesture commands", self._stop_commands),
        ):
            try:
                action()
            except Exception:
                logger.exception("Could not %s after a tracking failure", description)
        logger.error("Tracking failed", exc_info=(type(error), error, error.__traceback__))
        try:
            self.gui.show_failure(str(error) or type(error).__name__)
        except Exception:
            logger.exception("Could not display the tracking failure")
        finally:
            self.gui.quit()

    def _display(self, snapshot: EngineSnapshot) -> None:
        # A camera overlay shows the picture itself, so the preview window steps aside.
        overlay_camera = self.hand_tracking.shows_camera
        if overlay_camera != self._preview_hidden:
            self.preview.set_visible(not overlay_camera)
            self._preview_hidden = overlay_camera
        if snapshot.sequence == self._seen_sequence or snapshot.result is None:
            return
        self._seen_sequence = snapshot.sequence
        result, self._switches = snapshot.result, snapshot.switches
        self._show_statuses(result)
        self._hand_reports = result.hand_reports
        self._refresh_gesture_display()
        if result.frame is None:
            return
        with self.engine.frame_profiler.measure("preview.submit"):
            if overlay_camera:
                self.hand_tracking.show_frame(result.frame)
            else:
                self.preview.show(result.frame)

    def _show_statuses(self, result: FrameResult) -> None:
        """Update the model and camera status displays when they change."""
        if result.model_status != self._model_ui_state:
            self.hand_tracking.set_model_status(result.model_status)
            self._invalidate_gesture_display()
            self._model_ui_state = result.model_status
        if result.camera_status != self._camera_ui_state:
            with self.engine.frame_profiler.measure("ui.camera_status"):
                self.panels.main.update_camera_state(result.camera_status)
            self._camera_ui_state = result.camera_status

    def _refresh_gesture_display(self):
        """Report hand/gesture changes immediately; throttle ongoing finger data."""
        switches = self._switches
        snapshot = (
            switches.enabled, switches.paused, switches.commands_active,
            tuple(sorted(
                (report.display_key for report in self._hand_reports),
                key=lambda key: key[0],
            )),
        )
        now = time.monotonic()
        if not self._gesture_display.due(snapshot, now):
            return
        with self.engine.frame_profiler.measure("ui.gesture_display"):
            self.hand_tracking.update_data(
                self._hand_reports, enabled=switches.enabled,
                paused=switches.paused or (
                    not switches.commands_active and not self.hand_tracking.preview_active
                ),
            )
        self._gesture_display.mark(snapshot, now)

    def close(self):
        self.running = False
        if self._closed:
            return
        self._closed = True
        # Hide topmost surfaces first, then stop the engine thread so no further
        # keys are sent, then release input, inference and the camera.
        # ExitStack still attempts every cleanup when an earlier one raises.
        with ExitStack() as cleanup:
            cleanup.callback(self._garbage_collector.stop)
            cleanup.callback(self.preview.close)
            cleanup.callback(self.gui.close)
            cleanup.callback(self.engine.close)
            cleanup.callback(self.runner.stop)
            cleanup.callback(logger.info, "Application shutdown started")
            cleanup.callback(self.gui.hide_overlays)
        logger.info("Application shutdown finished")
