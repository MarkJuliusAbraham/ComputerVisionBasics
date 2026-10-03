import cv2


class HandDrawer:
    """Handles visualization of hand landmarks."""

    WRIST = 0

    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4

    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8

    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12

    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16

    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20

    def __init__(
        self,
        landmark_radius=3,
        landmark_color=(255, 255, 255),
    ):
        self.landmark_radius = landmark_radius
        self.landmark_color = landmark_color

        self.thumb_color = (255, 0, 0)
        self.index_color = (0, 255, 0)
        self.middle_color = (0, 0, 255)
        self.ring_color = (0, 255, 255)
        self.pinky_color = (255, 0, 255)
        self.knuckle_color = (255, 255, 255)

    def draw(self, frame, hands):
        height, width = frame.shape[:2]

        for hand in hands:
            self._draw_landmarks(frame, hand, width, height)

            self._draw_thumb(frame, hand, width, height)
            self._draw_index(frame, hand, width, height)
            self._draw_middle(frame, hand, width, height)
            self._draw_ring(frame, hand, width, height)
            self._draw_pinky(frame, hand, width, height)
            self._draw_knuckles(frame, hand, width, height)

    def _draw_landmarks(self, frame, hand, width, height):
        """Draw all hand landmarks."""

        for landmark in hand:
            x = int(landmark.x * width)
            y = int(landmark.y * height)

            cv2.circle(
                frame,
                (x, y),
                self.landmark_radius,
                self.landmark_color,
                -1,
            )

    def _draw_thumb(self, frame, hand, width, height):
        """Draw the thumb."""

        self._draw_portion(
            frame,
            hand,
            [self.THUMB_CMC, self.THUMB_MCP, self.THUMB_IP, self.THUMB_TIP],
            width,
            height,
            self.thumb_color,
        )

    def _draw_index(self, frame, hand, width, height):
        """Draw the index finger."""

        self._draw_portion(
            frame,
            hand,
            [self.INDEX_MCP, self.INDEX_PIP, self.INDEX_DIP, self.INDEX_TIP],
            width,
            height,
            self.index_color,
        )

    def _draw_middle(self, frame, hand, width, height):
        """Draw the middle finger."""

        self._draw_portion(
            frame,
            hand,
            [self.MIDDLE_MCP, self.MIDDLE_PIP, self.MIDDLE_DIP, self.MIDDLE_TIP],
            width,
            height,
            self.middle_color,
        )

    def _draw_ring(self, frame, hand, width, height):
        """Draw the ring finger."""

        self._draw_portion(
            frame,
            hand,
            [self.RING_MCP, self.RING_PIP, self.RING_DIP, self.RING_TIP],
            width,
            height,
            self.ring_color,
        )

    def _draw_pinky(self, frame, hand, width, height):
        """Draw the pinky finger."""

        self._draw_portion(
            frame,
            hand,
            [self.PINKY_MCP, self.PINKY_PIP, self.PINKY_DIP, self.PINKY_TIP],
            width,
            height,
            self.pinky_color,
        )

    def _draw_knuckles(self, frame, hand, width, height):
        """Draw the knuckle finger."""
        self._draw_portion(
            frame,
            hand,
            [5,9,13,17],
            width,
            height,
            self.knuckle_color
        )
    def _draw_portion(
        self,
        frame,
        hand,
        landmark_indices,
        width,
        height,
        color,
    ):
        """Draw a sequence of landmarks and the lines connecting them."""

        points = []

        for index in landmark_indices:
            landmark = hand[index]

            x = int(landmark.x * width)
            y = int(landmark.y * height)

            points.append((x, y))

            cv2.circle(
                frame,
                (x, y),
                self.landmark_radius,
                color,
                -1,
            )

        for start, end in zip(points, points[1:]):
            cv2.line(
                frame,
                start,
                end,
                color,
                2,
            )
