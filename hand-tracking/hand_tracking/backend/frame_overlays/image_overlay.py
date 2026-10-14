from pathlib import Path

import cv2


class ImageOverlay:
    def __init__(self):
        self.image = self.defaultImage()

    def defaultImage(self):

        print("Loading default image...")
        image_path = Path(__file__).parent / "images" / "absolute_cinema.jpg"

        image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)

        if image is None:
            raise FileNotFoundError(
                f"Could not load image: {image_path}"
            )

        return image
    def overlay(self, frame):
        # Make the image small enough to clearly see the camera
        image = cv2.resize(self.image, (200, 200))

        # Put it in the top-left corner
        frame[0:200, 0:200] = image

        return frame
