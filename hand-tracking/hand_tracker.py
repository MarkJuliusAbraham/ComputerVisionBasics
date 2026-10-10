from pathlib import Path

import cv2
import mediapipe as mp


MODEL_PATH = Path(__file__).resolve().parent / "tasks" / "hand_landmarker.task"


class HandTracker:
    """Handles MediaPipe hand landmark detection."""

    def __init__(
        self,
        model_path=MODEL_PATH,
        num_hands=1,
    ):
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=str(model_path)
            ),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7,
        )

        self.landmarker = (
            mp.tasks.vision.HandLandmarker
            .create_from_options(options)
        )

        self.timestamp_ms = 0

    def detect(self, frame):
        """Detect hands in an OpenCV BGR frame."""

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )

        self.timestamp_ms += 1

        return self.landmarker.detect_for_video(
            mp_image,
            self.timestamp_ms,
        )
