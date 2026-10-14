import time
import cv2
from contextlib import ExitStack
from dataclasses import dataclass

from app_components import FrameOverlays, HandPipeline, VideoIO
from gui_tkinter.control_window import ControlWindow as Gui
from gui_tkinter.core.state import ControlCallbacks, ControlWindowContext, PanelSet
from gui_tkinter.main_panel import MainPanel
from gui_tkinter.settings_panel import SettingsPanel
from gui_tkinter.tracking import TrackingWindowRegistry
from gui_tkinter.tracking.hand import HandTrackingActions, HandTrackingModule
from frame_profiler import FrameProfiler
from gestures.gesture_config import GestureConfig
from settings.settings_manager import Settings, SettingsData, SettingsValues


@dataclass
class TrackingSwitches:
    """The settings and user switches that decide whether hands are tracked."""

    enabled: bool | None = None     # "Enable hand tracking" setting
    paused: bool = False            # Pause/Resume tracking button
    commands_active: bool = False   # Debugging page visible or desktop overlay on

    def can_track(self, model_status) -> bool:
        """Detection is possible and neither the settings nor the user paused it."""
        return bool(model_status.can_detect and self.enabled and not self.paused)


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
    """Coordinates the application components."""

    def __init__(
        self, settings: Settings, video: VideoIO, pipeline: HandPipeline, overlays: FrameOverlays,
    ):
        self.settings = settings
        self.video = video
        self.pipeline = pipeline
        self.overlays = overlays
        self.theme = None
        self.switches = TrackingSwitches()
        self.frame_profiler = FrameProfiler(enabled=bool(settings.data.profile))
        self.apply_settings()

        self.running = True
        self.restart_requested = False
        self._camera_ui_state = None
        self._model_ui_state = None
        self._gesture_display = DisplayThrottle()
        self._latest_hand_states = []
        self.hand_tracking = HandTrackingModule(
            settings, HandTrackingActions(
                restart=self.restart_hand_tracking,
                toggle_pause=self.toggle_tracking,
                activity_changed=self.set_tracking_tab_active,
                apply_settings=self.apply_changes,
                apply_mapping=self.apply_gesture_config,
            ),
            model_asset=self.pipeline.tracker.asset,
        )
        tracking_modules = TrackingWindowRegistry((self.hand_tracking,))
        panels = PanelSet(main=MainPanel(tracking_modules), settings=SettingsPanel())
        self.panels = panels
        callbacks = ControlCallbacks(
            on_restart=self.request_restart,
            on_close=self.request_quit,
            on_settings_path=self.load_settings_file,
            on_apply=self.apply_changes,
            on_camera_switch=self.video.camera.request_switch,
        )
        context = ControlWindowContext(
            settings=settings,
            callbacks=callbacks,
            panels=panels,
            camera_index=self.video.camera.requested_index,
            tracking_modules=tracking_modules,
        )
        self.gui = Gui(context)

    def apply_settings(self):
        """Copy values from the settings object onto the app."""
        data = self.settings.data
        previously_enabled = self.switches.enabled
        self.pipeline.apply_settings(data)
        self.switches.enabled = data.track_hands
        if previously_enabled and not data.track_hands:
            self.pipeline.gestures.suspend()
        self.frame_profiler.enabled = bool(data.profile)
        self.theme = data.theme

    def load_settings_file(self, path: str) -> bool:
        """Called when the user browses to a different file."""
        if not self.gui.confirm_pending_changes():
            return False
        self.settings.use_file(path)
        self.apply_settings()
        self.gui.apply_display(self.settings.data)
        self.panels.settings.show_settings(self.settings)
        self.hand_tracking.reload_settings(self.settings)
        self._invalidate_gesture_display()
        return True

    def apply_changes(self, values: SettingsValues) -> SettingsData:
        """Apply only the fields owned by the settings panel that submitted them."""
        model_path = values.get("hand_landmarker_model_path")
        if model_path and model_path != self.settings.data.hand_landmarker_model_path:
            self.pipeline.tracker.asset.validate_path(model_path)
        data = self.settings.update_fields(values)
        self.apply_settings()
        self.gui.apply_display(data)
        self.panels.settings.rebase(self.settings, values)
        self.hand_tracking.synchronize(self.settings, values)
        self._invalidate_gesture_display()
        return data

    def apply_gesture_config(self, config: GestureConfig) -> None:
        """Apply a validated, saved gesture mapping to the running handler."""
        self.pipeline.gestures.configure(config)

    def request_restart(self) -> None:
        if not self.running:
            return
        camera = self.video.camera
        camera.request_switch(camera.requested_index)
        self._camera_ui_state = None
        self.restart_hand_tracking()

    def restart_hand_tracking(self) -> None:
        """Reset the hand pipeline without rebuilding windows or the shared camera."""
        if not self.running:
            return
        self.pipeline.restart(self.settings.data.hand_landmarker_model_path)
        self._latest_hand_states = []
        self._gesture_display.reset()
        self.switches.paused = False
        self.hand_tracking.debug.set_tracking_paused(False)
        self.overlays.invoker.reset()

    def request_quit(self) -> None:
        self.running = False
        self.gui.quit()

    def toggle_tracking(self) -> None:
        self.switches.paused = not self.switches.paused
        if self.switches.paused:
            self.pipeline.gestures.suspend()
        self.hand_tracking.debug.set_tracking_paused(self.switches.paused)

    def set_tracking_tab_active(self, active: bool) -> None:
        """The hand debugging page or enabled overlay can keep commands active."""
        self.switches.commands_active = active
        if not active:
            self.pipeline.gestures.suspend()
            self._latest_hand_states = []
        self._invalidate_gesture_display()

    def _clear_hand_states(self) -> None:
        """Forget the last frame's hands and force the next display refresh."""
        self._latest_hand_states = []
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
            fps = self.frame_profiler.finish_frame()
            if fps is not None:
                samples, average_ms, maximum_ms = self.pipeline.tracker.take_latency_stats()
                if samples:
                    print(
                        f"FPS: {fps:.1f} | detection latency "
                        f"submit→result avg/max: "
                        f"{average_ms:.2f}/{maximum_ms:.2f} ms"
                    )
                else:
                    print(f"FPS: {fps:.1f} | detection latency: no results")

    def _process_frame_work(self):
        """Run and measure the work for one event-loop frame."""
        pipeline, overlays, switches = self.pipeline, self.overlays, self.switches
        model_status = pipeline.tracker.model_status
        if model_status != self._model_ui_state:
            self.hand_tracking.set_model_status(model_status)
            pipeline.gestures.suspend()
            self._clear_hand_states()
            self._model_ui_state = model_status
        can_track = switches.can_track(model_status)
        with self.frame_profiler.measure("commands.update"):
            pipeline.gestures.update(allow_repeats=can_track and switches.commands_active)

        with self.frame_profiler.measure("camera.status"):
            camera_state = self.video.camera.status()
        if camera_state != self._camera_ui_state:
            with self.frame_profiler.measure("ui.camera_status"):
                self.panels.main.update_camera_state(camera_state)
            self._camera_ui_state = camera_state
        with self.frame_profiler.measure("camera.read_copy"):
            frame = self.video.camera.read()
        if frame is None:
            # A failed device should leave the controls available for choosing
            # another camera rather than terminating the whole application.
            self._latest_hand_states = []
            pipeline.gestures.finish_frame(set())
            self._refresh_gesture_display()
            self.video.preview.show(None)
            self.gui.after(10, self._process_frame)
            return

        if can_track and (switches.commands_active or self.hand_tracking.preview_active):
            with self.frame_profiler.measure("tracker.prepare_submit"):
                tracking = pipeline.tracker.detect(frame)
            with self.frame_profiler.measure("landmarks.draw"):
                overlays.landmarks.draw(frame, tracking.hand_landmarks)
            with self.frame_profiler.measure("frame.flip"):
                cv2.flip(frame, 1, dst=frame)  # in place, no new allocation
            with self.frame_profiler.measure("gestures.process"):
                self._latest_hand_states = pipeline.analyze(
                    frame, tracking, invoke_commands=switches.commands_active,
                )
                overlays.draw_hand_status(frame, self._latest_hand_states)
        else:
            with self.frame_profiler.measure("frame.flip"):
                cv2.flip(frame, 1, dst=frame)
            self._latest_hand_states = []

        with self.frame_profiler.measure("gesture_path.draw"):
            overlays.gesture_paths.draw(frame, pipeline.gestures.drawing_paths)

        self._refresh_gesture_display()

        # Once per frame, even when no hands are visible
        with self.frame_profiler.measure("overlay.compose"):
            frame = overlays.invoker.handleDisplay(frame)
        with self.frame_profiler.measure("preview.submit"):
            self.video.preview.show(frame)

        self.gui.after(1, self._process_frame)

    def _refresh_gesture_display(self):
        """Report hand/gesture changes immediately; throttle ongoing finger data."""
        switches = self.switches
        snapshot = (
            switches.enabled, switches.paused, switches.commands_active,
            tuple(sorted(
                (report.display_key for report in self._latest_hand_states),
                key=lambda key: key[0],
            )),
        )
        now = time.monotonic()
        if not self._gesture_display.due(snapshot, now):
            return
        with self.frame_profiler.measure("ui.gesture_display"):
            self.hand_tracking.update_data(
                self._latest_hand_states, enabled=switches.enabled,
                paused=switches.paused or (
                    not switches.commands_active and not self.hand_tracking.preview_active
                ),
            )
        self._gesture_display.mark(snapshot, now)

    def close(self):
        self.running = False
        # Run every cleanup even if an earlier one raises; the last
        # registered runs first: input and inference, then windows, then devices.
        with ExitStack() as cleanup:
            cleanup.callback(self.video.close)
            cleanup.callback(self.gui.close)
            cleanup.callback(self.pipeline.close)
