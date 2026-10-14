import cv2
import numpy as np


class GesturePathOverlay:
    """Render independent fingertip paths over the mirrored camera view."""

    def __init__(self, hand_drawer, thickness=1):
        self.hand_drawer = hand_drawer
        self.thickness = thickness

    def draw(self, frame, drawing_paths):
        height, width = frame.shape[:2]
        for drawing in drawing_paths:
            if not drawing.points:
                continue
            points = self._pixels(drawing.points, width, height)
            color = self.hand_drawer.color_for_finger(drawing.finger)
            if len(points) > 1:
                cv2.polylines(
                    frame, [points], False, color, self.thickness, lineType=cv2.LINE_AA,
                )
            if drawing.repeat_markers:
                markers = self._pixels(drawing.repeat_markers, width, height)
                for marker in markers:
                    center = tuple(int(value) for value in marker)
                    cv2.circle(
                        frame, center, 8, self.hand_drawer.landmark_color, 1,
                        lineType=cv2.LINE_AA,
                    )
                    cv2.circle(frame, center, 5, color, 1, lineType=cv2.LINE_AA)
            start = tuple(int(value) for value in points[0])
            end = tuple(int(value) for value in points[-1])
            cv2.circle(frame, start, 4, color, 1, lineType=cv2.LINE_AA)
            cv2.circle(frame, end, 3, color, -1, lineType=cv2.LINE_AA)
        return frame

    @staticmethod
    def _pixels(normalized_points, width, height):
        """Convert a path in one batch, matching the camera frame's mirror."""
        points = np.asarray(normalized_points, dtype=np.float64)[:, :2]
        np.clip(points, 0.0, 1.0, out=points)
        points[:, 0] = (1.0 - points[:, 0]) * (width - 1)
        points[:, 1] *= height - 1
        return np.rint(points).astype(np.int32)
