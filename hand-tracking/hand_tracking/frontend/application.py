import time
from contextlib import ExitStack
from dataclasses import dataclass

from hand_tracking.backend.engine.engine import FrameResult, TrackingEngine
from hand_tracking.backend.settings.settings_manager import SettingsData, SettingsValues
from hand_tracking.frontend.camera_preview import CameraPreview
from hand_tracking.frontend.control_window import ControlWindow as Gui
from hand_tracking.frontend.core.state import ControlCallbacks, ControlWindowContext, PanelSet
from hand_tracking.frontend.main_panel.main_panel import MainPanel
from hand_tracking.frontend.settings_panel.settings_panel import SettingsPanel
from hand_tracking.frontend.tracking.registry import TrackingWindowRegistry
from hand_tracking.frontend.tracking.hand.module import HandTrackingActions, HandTrackingModule


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
    """Runs the control windows and displays what the tracking engine produces."""

    def __init__(self, engine: TrackingEngine, preview: CameraPreview):
        self.engine = engine
        self.preview = preview
        settings = engine.settings

        self.running = True
        self.restart_requested = False
        self._camera_ui_state = None
        self._model_ui_state = None
        self._gesture_display = DisplayThrottle()
        self._hand_reports = []
        self.hand_tracking = HandTrackingModule(
            settings, HandTrackingActions(
                restart=self.restart_hand_tracking,
                toggle_pause=self.toggle_tracking,
                activity_changed=self.set_tracking_tab_active,
                apply_settings=self.apply_changes,
                apply_mapping=engine.apply_gesture_config,
            ),
            model_asset=engine.model_asset,
        )
        tracking_modules = TrackingWindowRegistry((self.hand_tracking,))
        panels = PanelSet(main=MainPanel(tracking_modules), settings=SettingsPanel())
        self.panels = panels
        callbacks = ControlCallbacks(
            on_restart=self.request_restart,
            on_close=self.request_quit,
            on_settings_path=self.load_settings_file,
            on_apply=self.apply_changes,
            on_camera_switch=engine.camera.request_switch,
        )
        context = ControlWindowContext(
            settings=settings,
            callbacks=callbacks,
            panels=panels,
            camera_index=engine.camera.requested_index,
            tracking_modules=tracking_modules,
        )
        self.gui = Gui(context)

    def load_settings_file(self, path: str) -> bool:
        """Called when the user browses to a different file."""
        if not self.gui.confirm_pending_changes():
            return False
        self.engine.use_settings_file(path)
        settings = self.engine.settings
        self.gui.apply_display(settings.data)
        self.panels.settings.show_settings(settings)
        self.hand_tracking.reload_settings(settings)
        self._invalidate_gesture_display()
        return True

    def apply_changes(self, values: SettingsValues) -> SettingsData:
        """Apply only the fields owned by the settings panel that submitted them."""
        data = self.engine.apply_changes(values)
        settings = self.engine.settings
        self.gui.apply_display(data)
        self.panels.settings.rebase(settings, values)
        self.hand_tracking.synchronize(settings, values)
        self._invalidate_gesture_display()
        return data

    def request_restart(self) -> None:
        if not self.running:
            return
        self.engine.restart_camera()
        self._camera_ui_state = None
        self.restart_hand_tracking()

    def restart_hand_tracking(self) -> None:
        """Reset the hand pipeline without rebuilding windows or the shared camera."""
        if not self.running:
            return
        self.engine.restart_hand_tracking()
        self._hand_reports = []
        self._gesture_display.reset()
        self.hand_tracking.debug.set_tracking_paused(False)

    def request_quit(self) -> None:
        self.running = False
        self.gui.quit()

    def toggle_tracking(self) -> None:
        paused = self.engine.toggle_pause()
        self.hand_tracking.debug.set_tracking_paused(paused)

    def set_tracking_tab_active(self, active: bool) -> None:
        """The hand debugging page or enabled overlay can keep commands active."""
        self.engine.set_commands_active(active)
        if not active:
            self._hand_reports = []
        self._invalidate_gesture_display()

    def _invalidate_gesture_display(self) -> None:
        self._gesture_display.invalidate()

    def run(self):
        try:
            self.gui.after(0, self._process_frame)
            self.gui.run()
        except KeyboardInterrupt:
            self.running = False
        finally:
            self.close()

    def _process_frame(self):
        """Process one frame, then yield to the control window's event loop."""
        if not self.running:
            return

        try:
            self._process_frame_work()
        finally:
            self.engine.finish_frame()

    def _process_frame_work(self):
        result = self.engine.process_frame(preview_requested=self.hand_tracking.preview_active)
        self._show_statuses(result)
        self._hand_reports = result.hand_reports
        self._refresh_gesture_display()

        if result.frame is None:
            self.gui.after(10, self._process_frame)
            return
        with self.engine.frame_profiler.measure("preview.submit"):
            self.preview.show(result.frame)
        self.gui.after(1, self._process_frame)

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
        switches = self.engine.switches
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
        # Run every cleanup even if an earlier one raises; the last registered
        # runs first: input, inference and the camera, then the windows.
        with ExitStack() as cleanup:
            cleanup.callback(self.preview.close)
            cleanup.callback(self.gui.close)
            cleanup.callback(self.engine.close)
