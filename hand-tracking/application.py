import cv2
import time
from custom_overlay import invoker_overlay
from custom_overlay.invoker_overlay import InvokerOverlay


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
    ):
        self.camera = camera
        self.tracker = tracker
        self.drawer = drawer
        self.debug_overlay = debug_overlay
        self.detector = detector
        self.gesture_handler = gesture_handler
        self.image_overlay = image_overlay
        self.invoker_overlay = invoker_overlay

    def run(self):
        while True:
            frame = self.camera.read()

            if frame is None:
                break

            result = self.tracker.detect(frame)

            self.drawer.draw(
                frame,
                result.hand_landmarks,
            )

            frame = cv2.flip(frame, 1)

            for hand, handedness in zip(
                result.hand_landmarks,
                result.handedness,
            ):
                side = handedness[0].category_name

                state = self.detector.update(
                    hand,
                    side,
                )

                self.debug_overlay.update(
                    frame,
                    state,
                )

                result = self.gesture_handler.handle(state)

                if result is not None:
                    self.invoker_overlay.addCommand(result)

                    if result == 'r':
                        self.invoker_overlay.pollResult()

                frame = self.invoker_overlay.handleDisplay(frame)


            cv2.imshow("Hand Tracking", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        self.close()

    def close(self):
        self.camera.release()
        self.tracker.close()
        cv2.destroyAllWindows()
