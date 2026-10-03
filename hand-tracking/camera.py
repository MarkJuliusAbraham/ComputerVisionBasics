import cv2


class Camera:
    """Handles webcam input."""

    def __init__(self, camera_index=0, width=1280, height=720):
        self.cap = cv2.VideoCapture(camera_index)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def read(self):
        success, frame = self.cap.read()

        if not success:
            return None

        return frame

    def release(self):
        self.cap.release()
