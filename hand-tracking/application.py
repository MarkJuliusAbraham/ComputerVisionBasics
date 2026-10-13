import time
import cv2
from contextlib import ExitStack

from gui_tkinter.control_window import ControlWindow as Gui
from gui_tkinter.core.state import ControlCallbacks, ControlWindowContext, PanelSet
from gui_tkinter.main_panel import MainPanel
from gui_tkinter.settings_panel import SettingsPanel
from gui_tkinter.tracking import TrackingWindowRegistry
from gui_tkinter.tracking.hand import HandTrackingActions, HandTrackingModule
from frame_profiler import FrameProfiler
from gesture_path_overlay import GesturePathOverlay
from gestures.gesture_config import GestureConfig
from settings.settings_manager import Settings, SettingsData, SettingsValues


class Application:
    """Coordinates the application components."""

    def __init__(
        self,
        camera,
        tracker,
        drawer,
        debug_overlay,
        detector,
        gesture_handler,
        image_overlay,
        invoker_overlay,
        settings: Settings,
        *,
        preview,
    ):
        self.profile = None
        self.theme = None
        self.track_hands = None
        self.camera = camera
        self.preview = preview
        self.tracker = tracker
        self.drawer = drawer
        self.debug_overlay = debug_overlay
        self.detector = detector
        self.gesture_handler = gesture_handler
        self.gesture_path_overlay = GesturePathOverlay(drawer)
        self.image_overlay = image_overlay
        self.invoker_overlay = invoker_overlay
        self.settings = settings
        self.frame_profiler = FrameProfiler(enabled=bool(settings.data.profile))
        self.apply_settings()

        self.running = True
        self.restart_requested = False
        self.tracking_paused = False
        self._tracking_tab_active = False
        self._camera_ui_state = None
        self._model_ui_state = None
        self._gesture_display_updated = 0.0
        self._gesture_display_snapshot = None
        self._latest_hand_states = []
        self.hand_tracking = HandTrackingModule(
            settings, HandTrackingActions(
                restart=self.restart_hand_tracking,
                toggle_pause=self.toggle_tracking,
                activity_changed=self.set_tracking_tab_active,
                apply_settings=self.apply_changes,
                apply_mapping=self.apply_gesture_config,
            ),
            model_asset=self.tracker.asset,
        )
        tracking_modules = TrackingWindowRegistry((self.hand_tracking,))
        panels = PanelSet(main=MainPanel(tracking_modules), settings=SettingsPanel())
        self.panels = panels
        callbacks = ControlCallbacks(
            on_restart=self.request_restart,
            on_close=self.request_quit,
            on_settings_path=self.load_settings_file,
            on_apply=self.apply_changes,
            on_camera_switch=self.camera.request_switch,
        )
        context = ControlWindowContext(
            settings=settings,
            callbacks=callbacks,
            panels=panels,
            camera_index=self.camera.requested_index,
            tracking_modules=tracking_modules,
        )
        self.gui = Gui(context)


    def apply_settings(self):
        """Copy values from the settings object onto the app."""
        previously_enabled = self.track_hands
        self.detector.configure(self.settings.data)
        self.gesture_handler.configure_optimistic(self.settings.data.optimistic_tracking)
        self.tracker.request_model(self.settings.data.hand_landmarker_model_path)
        self.track_hands = self.settings.data.track_hands
        if previously_enabled and not self.track_hands:
            self.gesture_handler.suspend()
        self.profile = self.settings.data.profile
        self.frame_profiler.enabled = bool(self.profile)
        self.theme = self.settings.data.theme

    def load_settings_file(self, path: str) -> bool:
        """Called when the user browses to a different file."""
        if not self.gui.confirm_pending_changes():
            return False
        self.settings.use_file(path)
        self.apply_settings()
        self.gui.apply_display(self.settings.data)
        self.panels.settings.show_settings(self.settings)
        self.hand_tracking.reload_settings(self.settings)
        self._gesture_display_snapshot = None
        return True

    def apply_changes(self, values: SettingsValues) -> SettingsData:
        """Apply only the fields owned by the settings panel that submitted them."""
        model_path = values.get("hand_landmarker_model_path")
        if model_path and model_path != self.settings.data.hand_landmarker_model_path:
            self.tracker.asset.validate_path(model_path)
        data = self.settings.update_fields(values)
        self.apply_settings()
        self.gui.apply_display(data)
        self.panels.settings.rebase(self.settings, values)
        self.hand_tracking.synchronize(self.settings, values)
        self._gesture_display_snapshot = None
        return data

    def apply_gesture_config(self, config: GestureConfig) -> None:
        """Apply a validated, saved gesture mapping to the running handler."""
        self.gesture_handler.configure(config)

    def request_restart(self) -> None:
        if not self.running:
            return
        self.camera.request_switch(self.camera.requested_index)
        self._camera_ui_state = None
        self.restart_hand_tracking()

    def restart_hand_tracking(self) -> None:
        """Reset the hand pipeline without rebuilding windows or the shared camera."""
        if not self.running:
            return
        self.tracker.request_model(self.settings.data.hand_landmarker_model_path, force=True)
        self.gesture_handler.configure(self.gesture_handler.config)
        self._latest_hand_states = []
        self._gesture_display_updated = 0.0
        self._gesture_display_snapshot = None
        self.tracking_paused = False
        self.hand_tracking.debug.set_tracking_paused(False)
        self.invoker_overlay.spell_stack.clear()
        self.invoker_overlay.current_image = None
        self.invoker_overlay.image_expiry = 0

    def request_quit(self) -> None:
        self.running = False
        self.gui.quit()

    def toggle_tracking(self) -> None:
        self.tracking_paused = not self.tracking_paused
        if self.tracking_paused:
            self.gesture_handler.suspend()
        self.hand_tracking.debug.set_tracking_paused(self.tracking_paused)

    def set_tracking_tab_active(self, active: bool) -> None:
        """Only the hand window's visible Debugging page can invoke commands."""
        self._tracking_tab_active = active
        if not active:
            self.gesture_handler.suspend()
            self._latest_hand_states = []
        self._gesture_display_snapshot = None

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
                samples, average_ms, maximum_ms = self.tracker.take_latency_stats()
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
        model_status = self.tracker.model_status
        if model_status != self._model_ui_state:
            self.hand_tracking.set_model_status(model_status)
            self.gesture_handler.suspend()
            self._latest_hand_states = []
            self._gesture_display_snapshot = None
            self._model_ui_state = model_status
        with self.frame_profiler.measure("commands.update"):
            self.gesture_handler.update(
                allow_repeats=model_status.can_detect and self.track_hands
                and not self.tracking_paused and self._tracking_tab_active
            )

        with self.frame_profiler.measure("camera.status"):
            camera_state = self.camera.status()
        if camera_state != self._camera_ui_state:
            with self.frame_profiler.measure("ui.camera_status"):
                self.panels.main.update_camera_state(*camera_state)
            self._camera_ui_state = camera_state
        with self.frame_profiler.measure("camera.read_copy"):
            frame = self.camera.read()
        if frame is None:
            # A failed device should leave the controls available for choosing
            # another camera rather than terminating the whole application.
            self._latest_hand_states = []
            self.gesture_handler.finish_frame(set())
            self._refresh_gesture_display()
            self.preview.show(None)
            self.gui.after(10, self._process_frame)
            return

        preview_active = self.hand_tracking.preview_active
        if (
            model_status.can_detect and self.track_hands and not self.tracking_paused
            and (self._tracking_tab_active or preview_active)
        ):
            with self.frame_profiler.measure("tracker.prepare_submit"):
                tracking = self.tracker.detect(frame)
            with self.frame_profiler.measure("landmarks.draw"):
                self.drawer.draw(frame, tracking.hand_landmarks)
            with self.frame_profiler.measure("frame.flip"):
                cv2.flip(frame, 1, dst=frame)  # in place, no new allocation
            with self.frame_profiler.measure("gestures.process"):
                self._latest_hand_states = self.process_hands(
                    frame, tracking, invoke_commands=self._tracking_tab_active
                )
        else:
            with self.frame_profiler.measure("frame.flip"):
                cv2.flip(frame, 1, dst=frame)
            self._latest_hand_states = []

        with self.frame_profiler.measure("gesture_path.draw"):
            self.gesture_path_overlay.draw(frame, self.gesture_handler.drawing_paths)

        self._refresh_gesture_display()

        # Once per frame, even when no hands are visible
        with self.frame_profiler.measure("overlay.compose"):
            frame = self.invoker_overlay.handleDisplay(frame)
        with self.frame_profiler.measure("preview.submit"):
            self.preview.show(frame)

        self.gui.after(1, self._process_frame)

    def _refresh_gesture_display(self):
        """Report hand/gesture changes immediately; throttle ongoing finger data."""
        snapshot = (
            self.track_hands, self.tracking_paused, self._tracking_tab_active,
            tuple(
                (record["handedness"], record["state"].palm, record["gesture"])
                for record in sorted(
                    self._latest_hand_states, key=lambda record: record["handedness"]
                )
            ),
        )
        now = time.monotonic()
        if (
            snapshot == self._gesture_display_snapshot
            and now - self._gesture_display_updated < 0.1
        ):
            return
        with self.frame_profiler.measure("ui.gesture_display"):
            self.hand_tracking.update_data(
                self._latest_hand_states, enabled=self.track_hands,
                paused=self.tracking_paused or (
                    not self._tracking_tab_active and not self.hand_tracking.preview_active
                ),
            )
        self._gesture_display_snapshot = snapshot
        self._gesture_display_updated = now

    def process_hands(self, frame, tracking, invoke_commands=True):
        hand_states = []
        for hand, handedness in zip(tracking.hand_landmarks, tracking.handedness):
            classification = handedness[0]
            hand_name = classification.category_name
            state = self.detector.update(hand, hand_name)
            self.debug_overlay.update(frame, state)

            gesture = self.gesture_handler.handle(
                state,
                hand_name,
                frame_size=(frame.shape[1], frame.shape[0]),
                invoke_commands=invoke_commands,
            )
            hand_states.append({
                "handedness": hand_name,
                "state": state,
                "gesture": gesture,
            })
        self.gesture_handler.finish_frame(
            {record["handedness"] for record in hand_states}, invoke_commands=invoke_commands,
        )
        return hand_states


    def close(self):
        self.running = False
        # Run every cleanup even if an earlier resource raises while closing.
        with ExitStack() as cleanup:
            cleanup.callback(self.tracker.close)
            cleanup.callback(self.camera.release)
            cleanup.callback(self.gui.close)
            cleanup.callback(self.preview.close)
            cleanup.callback(self.gesture_handler.close)
