import cv2
from hand_tracking.backend.gestures.finger_classifier import FingerPosition
from hand_tracking.backend.gestures.hand_landmarks import FINGER_NAMES, finger_label


class DebugOverlay:
    """Draws debugging information onto a frame."""

    POSITION_COLORS = {
        FingerPosition.STRAIGHT: (0, 255, 0),
        FingerPosition.PARTIAL: (0, 165, 255),
    }
    DEFAULT_POSITION_COLOR = (0, 0, 255)

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

    def _text(self, frame, text, origin, color):
        cv2.putText(frame, text, origin, self.font, self.font_scale, color, self.thickness)

    def _draw_finger_status(self, frame, gesture_state):
        for row, name in enumerate(FINGER_NAMES):
            finger = gesture_state.fingers[name]
            text = f"{finger_label(name)}: {finger.deviation:.1f} deg {finger.position.value}"
            color = self.POSITION_COLORS.get(finger.position, self.DEFAULT_POSITION_COLOR)
            self._text(frame, text, (20, 100 + 25 * row), color)

    def _draw_gesture(self, frame, gesture_state):
        self._text(frame, f"Fingers up: {gesture_state.fingers_up}", (20, 30), self.color)
        self._text(frame, f"Palm: {gesture_state.palm.value}", (20, 55), self.color)
