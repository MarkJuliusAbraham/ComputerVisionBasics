import cv2
from gestures.gesture_detector import Pinching
from gestures.finger_classifier import FingerPosition
from volume_controller import VolumeController


class DebugOverlay:
    """Draws debugging information onto a frame."""

    def __init__(
        self,
        volume = VolumeController(),
        color=(0, 255, 0),
        font_scale=0.4,
        thickness=2,
    ):
        self.volume = volume
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
        gesture = gesture_state.gesture
        palm = gesture_state.palm

        cv2.putText(
            frame,
            f"Gesture: {gesture}"
            f"FingerCount: {gesture_state.fingers_up}"
            ,
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

        if isinstance(gesture, Pinching):
            height, width = frame.shape[:2]

            x = int((1.0 - gesture.current_pos[0]) * width)
            y = int(gesture.current_pos[1] * height)

            volume_text = f"Volume: {self.volume.level * 100:.0f}%"

            cv2.putText(
                frame,
                volume_text,
                (x + 10, y),
                self.font,
                self.font_scale,
                self.color,
                self.thickness,
            )
