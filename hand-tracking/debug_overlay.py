import cv2
from gestures.finger_classifier import FingerPosition


class DebugOverlay:
    """Draws debugging information onto a frame."""

    def __init__(
        self,
        color=(0, 255, 0),
        font_scale=0.4,
        thickness=2,
    ):
        self.color = color
        self.font_scale = font_scale
        self.thickness = thickness
        self.font = cv2.FONT_HERSHEY_SIMPLEX

    def update(self, frame, gesture_state):
        self._draw_gesture(frame, gesture_state)
        self._draw_finger_status(frame, gesture_state)

    def _draw_finger_status(self, frame, gesture_state):
        fingers = [
            ("Thumb", gesture_state.fingers["thumb"]),
            ("Index", gesture_state.fingers["index"]),
            ("Middle", gesture_state.fingers["middle"]),
            ("Ring", gesture_state.fingers["ring"]),
            ("Pinky", gesture_state.fingers["pinky"]),
        ]

        y_position = 100

        for name, finger in fingers:
            text = (
                f"{name}: "
                f"{finger.deviation:.1f} deg "
                f"{finger.position.value}"
            )

            if finger.position == FingerPosition.STRAIGHT:
                color = (0, 255, 0)
            elif finger.position == FingerPosition.PARTIAL:
                color = (0, 165, 255)
            else:
                color = (0, 0, 255)

            cv2.putText(
                frame,
                text,
                (20, y_position),
                self.font,
                self.font_scale,
                color,
                self.thickness,
            )

            y_position += 25

    def _draw_gesture(self, frame, gesture_state):
        palm = gesture_state.palm

        cv2.putText(
            frame,
            f"Fingers up: {gesture_state.fingers_up}",
            (20, 30),
            self.font,
            self.font_scale,
            self.color,
            self.thickness,
        )
        cv2.putText(
            frame,
            f"Palm: {palm.value}",
            (20, 55),
            self.font,
            self.font_scale,
            self.color,
            self.thickness,
        )
