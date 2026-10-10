import time
import cv2


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
        profile=False,
    ):
        self.camera = camera
        self.tracker = tracker
        self.drawer = drawer
        self.debug_overlay = debug_overlay
        self.detector = detector
        self.gesture_handler = gesture_handler
        self.image_overlay = image_overlay
        self.invoker_overlay = invoker_overlay
        self.profile = profile

    def run(self):
        timings = {"read": 0.0, "track": 0.0, "logic": 0.0, "show": 0.0}
        frames = 0
        last_report = time.perf_counter()
        pc = time.perf_counter

        while True:
            t0 = pc()
            frame = self.camera.read()
            if frame is None:
                break
            t1 = pc()

            tracking = self.tracker.detect(frame)
            t2 = pc()

            self.drawer.draw(frame, tracking.hand_landmarks)
            cv2.flip(frame, 1, dst=frame)  # in place, no new allocation

            for hand, handedness in zip(
                tracking.hand_landmarks,
                tracking.handedness,
            ):
                side = handedness[0].category_name
                state = self.detector.update(hand, side)
                self.debug_overlay.update(frame, state)

                command = self.gesture_handler.handle(state)
                if command is not None:
                    self.invoker_overlay.addCommand(command)
                    if command == "r":
                        self.invoker_overlay.pollResult()

            # Once per frame, even when no hands are visible
            frame = self.invoker_overlay.handleDisplay(frame)
            t3 = pc()

            cv2.imshow("Hand Tracking", frame)
            key = cv2.waitKey(1) & 0xFF
            t4 = pc()

            if self.profile:
                timings["read"] += t1 - t0
                timings["track"] += t2 - t1
                timings["logic"] += t3 - t2
                timings["show"] += t4 - t3
                frames += 1
                if t4 - last_report >= 2.0:
                    avg = {k: v / frames * 1000 for k, v in timings.items()}
                    fps = frames / (t4 - last_report)
                    print(
                        f"{fps:5.1f} fps | "
                        + " | ".join(f"{k} {v:5.1f}ms" for k, v in avg.items())
                    )
                    timings = {k: 0.0 for k in timings}
                    frames = 0
                    last_report = t4

            if key == ord("q"):
                break

        self.close()

    def close(self):
        self.camera.release()
        self.tracker.close()
        cv2.destroyAllWindows()