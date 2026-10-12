import cv2


class GesturePathOverlay:
    """Draw a selected fingertip's gesture path over the mirrored camera view."""

    def __init__(self, hand_drawer, thickness=3):
        self.hand_drawer = hand_drawer
        self.thickness = thickness

    def draw(self, frame, drawing_path):
        if not drawing_path:
            return frame

        finger_name, normalized_points, repeat_markers = drawing_path
        if not normalized_points:
            return frame

        height, width = frame.shape[:2]
        points = [
            (
                round((1.0 - min(max(x, 0.0), 1.0)) * (width - 1)),
                round(min(max(y, 0.0), 1.0) * (height - 1)),
            )
            for x, y in normalized_points
        ]
        color = self.hand_drawer.color_for_finger(finger_name)

        for start, end in zip(points, points[1:]):
            cv2.line(
                frame, start, end, color, self.thickness, lineType=cv2.LINE_AA
            )

        for x, y in repeat_markers:
            marker = (
                round((1.0 - min(max(x, 0.0), 1.0)) * (width - 1)),
                round(min(max(y, 0.0), 1.0) * (height - 1)),
            )
            cv2.circle(frame, marker, 10, (255, 255, 255), 3, lineType=cv2.LINE_AA)
            cv2.circle(frame, marker, 7, color, 2, lineType=cv2.LINE_AA)

        cv2.circle(frame, points[0], 6, color, 2, lineType=cv2.LINE_AA)
        cv2.circle(frame, points[-1], 5, color, -1, lineType=cv2.LINE_AA)
        return frame
