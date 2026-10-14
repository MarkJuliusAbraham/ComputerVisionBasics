import cv2

from hand_tracking.gestures.hand_landmarks import FINGER_JOINTS, KNUCKLES


class HandDrawer:
    """Handles visualization of hand landmarks."""

    # BGR drawing colors per finger chain.
    FINGER_COLORS = {
        "thumb": (255, 0, 0),
        "index": (0, 255, 0),
        "middle": (0, 0, 255),
        "ring": (0, 255, 255),
        "pinky": (255, 0, 255),
    }
    KNUCKLE_COLOR = (255, 255, 255)
    LINE_THICKNESS = 2

    def __init__(
        self,
        landmark_radius=3,
        landmark_color=(255, 255, 255),
    ):
        self.landmark_radius = landmark_radius
        self.landmark_color = landmark_color

    def color_for_finger(self, finger_name):
        return self.FINGER_COLORS[finger_name]

    def draw(self, frame, hands):
        height, width = frame.shape[:2]

        for hand in hands:
            # Convert each landmark to pixels once; chains reuse the points.
            points = [(int(landmark.x * width), int(landmark.y * height)) for landmark in hand]
            for center in points:
                cv2.circle(frame, center, self.landmark_radius, self.landmark_color, -1)
            for name, joints in FINGER_JOINTS.items():
                self._draw_chain(frame, points, joints, self.FINGER_COLORS[name])
            self._draw_chain(frame, points, KNUCKLES, self.KNUCKLE_COLOR)

    def _draw_chain(self, frame, points, landmark_indices, color):
        """Draw a sequence of landmarks and the lines connecting them."""
        chain = [points[index] for index in landmark_indices]
        for center in chain:
            cv2.circle(frame, center, self.landmark_radius, color, -1)
        for start, end in zip(chain, chain[1:]):
            cv2.line(frame, start, end, color, self.LINE_THICKNESS)
