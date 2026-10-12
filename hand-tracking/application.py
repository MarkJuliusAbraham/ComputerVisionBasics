import time
import cv2

from control_panel.control_window import ControlWindow
from frame_profiler import FrameProfiler
from gesture_path_overlay import GesturePathOverlay


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
        settings,
    ):
        self.profile = None
        self.theme = None
        self.track_hands = None
        self.camera = camera
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
        self._tracking_tab_active = True
        self._camera_ui_state = None
        self._gesture_display_updated = 0.0
        self._latest_hand_states = []
        self.control_window = ControlWindow(
            self.request_restart,
            self.request_quit,
            settings=settings,
            on_settings_path=self.load_settings_file,
            on_apply=self.apply_changes,
            camera_index=self.camera.requested_index,
            on_camera_switch=self.camera.request_switch,
            on_toggle_tracking=self.toggle_tracking,
            on_tracking_tab_active=self.set_tracking_tab_active,
            on_mapping_saved=self.apply_gesture_config,
        )


    def apply_settings(self):
        """Copy values from the settings object onto the app."""
        self.detector.configure(self.settings.data)
        self.track_hands = self.settings.data.track_hands
        self.profile = self.settings.data.profile
        self.frame_profiler.enabled = bool(self.profile)
        self.theme = self.settings.data.theme

    def load_settings_file(self, path):
        """Called when the user browses to a different file."""
        self.settings.use_file(path)
        self.apply_settings()
        self.control_window.show_settings(self.settings)

    def apply_changes(self, data):
        """Called when the user clicks Apply in the GUI."""
        self.settings.update(data)
        self.apply_settings()

    def apply_gesture_config(self, config):
        """Apply a validated, saved gesture mapping to the running handler."""
        self.gesture_handler.configure(config)

    def request_restart(self):
        self.restart_requested = True
        self.running = False
        self.control_window.quit()

    def request_quit(self):
        self.running = False
        self.control_window.quit()

    def toggle_tracking(self):
        self.tracking_paused = not self.tracking_paused
        self.control_window.set_tracking_paused(self.tracking_paused)

    def set_tracking_tab_active(self, active):
        """Suspend hand detection while the Main tab is not visible."""
        self._tracking_tab_active = active

    def run(self):
        try:
            self.control_window.after(0, self._process_frame)
            self.control_window.run()
        except KeyboardInterrupt:
            self.running = False
        finally:
            self.close()

    def _process_frame(self):
        """Process one frame, then yield to Tk's event loop."""
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
        with self.frame_profiler.measure("commands.update"):
            self.gesture_handler.update()

        with self.frame_profiler.measure("camera.status"):
            camera_state = self.camera.status()
        if camera_state != self._camera_ui_state:
            with self.frame_profiler.measure("ui.camera_status"):
                self.control_window.update_camera_state(*camera_state)
            self._camera_ui_state = camera_state
        with self.frame_profiler.measure("camera.read_copy"):
            frame = self.camera.read()
        if frame is None:
            if self.camera.switching or self.camera.cap is None:
                with self.frame_profiler.measure("opencv.wait_key"):
                    cv2.waitKey(1)
                self.control_window.after(10, self._process_frame)
                return
            self.request_quit()
            return

        if self.track_hands and not self.tracking_paused and self._tracking_tab_active:
            with self.frame_profiler.measure("tracker.prepare_submit"):
                tracking = self.tracker.detect(frame)
            with self.frame_profiler.measure("landmarks.draw"):
                self.drawer.draw(frame, tracking.hand_landmarks)
            with self.frame_profiler.measure("frame.flip"):
                cv2.flip(frame, 1, dst=frame)  # in place, no new allocation
            with self.frame_profiler.measure("gestures.process"):
                self._latest_hand_states = self.process_hands(frame, tracking)
        else:
            with self.frame_profiler.measure("frame.flip"):
                cv2.flip(frame, 1, dst=frame)
            self._latest_hand_states = []

        with self.frame_profiler.measure("gesture_path.draw"):
            self.gesture_path_overlay.draw(frame, self.gesture_handler.drawing_path)

        now = time.monotonic()
        if now - self._gesture_display_updated >= 0.1:
            with self.frame_profiler.measure("ui.gesture_display"):
                self.control_window.update_gesture_display(
                    self._latest_hand_states,
                    enabled=self.track_hands,
                    paused=self.tracking_paused,
                )
            self._gesture_display_updated = now

        # Once per frame, even when no hands are visible
        with self.frame_profiler.measure("overlay.compose"):
            frame = self.invoker_overlay.handleDisplay(frame)
        with self.frame_profiler.measure("opencv.imshow"):
            cv2.imshow("Hand Tracking", frame)
        with self.frame_profiler.measure("opencv.wait_key"):
            cv2.waitKey(1)

        self.control_window.after(1, self._process_frame)

    def process_hands(self, frame, tracking):
        hand_states = []
        for hand, handedness in zip(tracking.hand_landmarks, tracking.handedness):
            classification = handedness[0]
            hand_name = classification.category_name
            state = self.detector.update(hand, hand_name)
            self.debug_overlay.update(frame, state)

            command = self.gesture_handler.handle(
                state,
                hand_name,
                frame_size=(frame.shape[1], frame.shape[0]),
            )
            hand_states.append({
                "handedness": hand_name,
                "state": state,
                "command": command,
            })
        return hand_states


    def close(self):
        # Join any in-flight camera switch before releasing shared resources.
        self.gesture_handler.close()
        self.control_window.close()
        self.camera.release()
        self.tracker.close()
        cv2.destroyAllWindows()
