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
        self.control_window = ControlWindow(
            self.request_restart,
            self.request_quit,
            settings=settings,
            on_settings_path=self.load_settings_file,
            on_apply=self.apply_changes,
        )


    def apply_settings(self):
        """Copy values from the settings object onto the app."""
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

    def request_quit(self):
        self.running = False

    def run(self):
        frames = 0
        last_report = time.perf_counter()

        while self.running:
            frame = self.camera.read()
            if frame is None:
                break

            if self.track_hands:
                tracking = self.tracker.detect(frame)
                self.drawer.draw(frame, tracking.hand_landmarks)
                cv2.flip(frame, 1, dst=frame)  # in place, no new allocation
                self.process_hands(frame, tracking)
            else:
                cv2.flip(frame, 1, dst=frame)

            # Once per frame, even when no hands are visible
            frame = self.invoker_overlay.handleDisplay(frame)

            cv2.imshow("Hand Tracking", frame)
            key = cv2.waitKey(1) & 0xFF

            # Process Tk events once per frame (non-blocking)
            self.control_window.update()

            if self.profile:
                frames += 1
                now = time.perf_counter()
                if now - last_report >= 2.0:
                    mode = "tracking" if self.track_hands else "no tracking"
                    print(f"{frames / (now - last_report):.1f} fps ({mode})")
                    frames = 0
                    last_report = now

            if key == ord("q"):
                break
            if key == ord("t"):
                self.settings.toggle("track_hands")
                self.apply_settings()
                self.control_window.show_settings(self.settings)
                frames = 0
                last_report = time.perf_counter()

        self.close()

    def process_hands(self, frame, tracking):
        for hand, handedness in zip(tracking.hand_landmarks, tracking.handedness):
            state = self.detector.update(hand, handedness[0].category_name)
            self.debug_overlay.update(frame, state)

            command = self.gesture_handler.handle(state)
            if command is not None:
                self.invoker_overlay.addCommand(command)


    def close(self):
        self.camera.release()
        self.tracker.close()
        self.control_window.close()
        cv2.destroyAllWindows()
