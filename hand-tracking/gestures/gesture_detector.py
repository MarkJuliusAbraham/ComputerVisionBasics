from dataclasses import dataclass

from .finger_classifier import FingerPosition, FingerState
from .geometry import distance


@dataclass(frozen=True)
class Pinching:
    distance: float
    start_pos: tuple[float, float]
    current_pos: tuple[float, float]


class GestureDetector:
    THUMB_TIP = 4
    INDEX_TIP = 8

    PINCH_DISTANCE_THRESHOLD = 0.05
    PINCH_RELEASE_FACTOR = 1.1

    def detect(
        self,
        hand,
        fingers: dict[str, FingerState],
        previous: Pinching | None,
    ) -> Pinching | None:
        distance_between_fingers = distance(
            hand[self.THUMB_TIP],
            hand[self.INDEX_TIP],
            include_z=False,
        )

        threshold = self.PINCH_DISTANCE_THRESHOLD

        if previous is not None:
            threshold *= self.PINCH_RELEASE_FACTOR

        is_pinching = (
            distance_between_fingers < threshold
            and fingers["index"].position != FingerPosition.CURLED
            and fingers["middle"].position == FingerPosition.CURLED
            and fingers["ring"].position == FingerPosition.CURLED
            and fingers["pinky"].position == FingerPosition.CURLED
        )

        if not is_pinching:
            return None

        current_pos = (
            hand[self.THUMB_TIP].x,
            hand[self.THUMB_TIP].y,
        )

        start_pos = (
            previous.start_pos
            if previous is not None
            else current_pos
        )

        return Pinching(
            distance=distance_between_fingers,
            start_pos=start_pos,
            current_pos=current_pos,
        )
