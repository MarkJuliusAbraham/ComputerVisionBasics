import time
import cv2

from control_panel.control_window import ControlWindow


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
        self._last_report = None
        self._frames = None
        self.profile = None
        self.theme = None
        self.track_hands = None
        self.camera = camera
        self.tracker = tracker
        self.drawer = drawer
        self.debug_overlay = debug_overlay
        self.detector = detector
        self.gesture_handler = gesture_handler
        self.image_overlay = image_overlay
        self.invoker_overlay = invoker_overlay
        self.settings = settings
        self.apply_settings()

        self.running = True
        self.restart_requested = False
        self.tracking_paused = False
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
        )


    def apply_settings(self):
        """Copy values from the settings object onto the app."""
        self.detector.configure(self.settings.data)
        self.track_hands = self.settings.data.track_hands
        self.profile = self.settings.data.profile
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

    def run(self):
        self._frames = 0
        self._last_report = time.perf_counter()
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

        camera_state = self.camera.status()
        if camera_state != self._camera_ui_state:
            self.control_window.update_camera_state(*camera_state)
            self._camera_ui_state = camera_state
        frame = self.camera.read()
        if frame is None:
            if self.camera.switching or self.camera.cap is None:
                cv2.waitKey(1)
                self.control_window.after(10, self._process_frame)
                return
            self.request_quit()
            return

        if self.track_hands and not self.tracking_paused:
            tracking = self.tracker.detect(frame)
            self.drawer.draw(frame, tracking.hand_landmarks)
            cv2.flip(frame, 1, dst=frame)  # in place, no new allocation
            self._latest_hand_states = self.process_hands(frame, tracking)
        else:
            cv2.flip(frame, 1, dst=frame)
            self._latest_hand_states = []

        now = time.monotonic()
        if now - self._gesture_display_updated >= 0.1:
            self.control_window.update_gesture_display(
                self._latest_hand_states,
                enabled=self.track_hands,
                paused=self.tracking_paused,
            )
            self._gesture_display_updated = now

        # Once per frame, even when no hands are visible
        frame = self.invoker_overlay.handleDisplay(frame)
        cv2.imshow("Hand Tracking", frame)
        key = cv2.waitKey(1) & 0xFF

        if self.profile:
            self._frames += 1
            now = time.perf_counter()
            if now - self._last_report >= 2.0:
                mode = "tracking" if self.track_hands else "no tracking"
                print(f"{self._frames / (now - self._last_report):.1f} fps ({mode})")
                self._frames = 0
                self._last_report = now

        self.control_window.after(1, self._process_frame)

    def process_hands(self, frame, tracking):
        hand_states = []
        for hand, handedness in zip(tracking.hand_landmarks, tracking.handedness):
            classification = handedness[0]
            hand_name = classification.category_name
            state = self.detector.update(hand, hand_name)
            self.debug_overlay.update(frame, state)

            command = self.gesture_handler.handle(state)
            hand_states.append({
                "handedness": hand_name,
                "state": state,
                "command": command,
            })
            if command is not None:
                self.invoker_overlay.addCommand(command)
        return hand_states


    def close(self):
        # Join any in-flight camera switch before releasing shared resources.
        self.control_window.close()
        self.camera.release()
        self.tracker.close()
        cv2.destroyAllWindows()
