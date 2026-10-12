from dataclasses import dataclass

from .finger_classifier import FingerState
from .geometry import distance


@dataclass(frozen=True)
class Pinching:
    distance: float
    start_pos: tuple[float, float]
    current_pos: tuple[float, float]


class GestureDetector:
    THUMB_TIP = 4
    INDEX_TIP = 8

    def __init__(self, distance_threshold, release_factor):
        self.distance_threshold = distance_threshold
        self.release_factor = release_factor

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

        threshold = self.distance_threshold

        if previous is not None:
            threshold *= self.release_factor

        is_pinching = (
            distance_between_fingers < threshold
            and fingers["index"].position.semantic_class != "curled"
            and fingers["middle"].position.semantic_class == "curled"
            and fingers["ring"].position.semantic_class == "curled"
            and fingers["pinky"].position.semantic_class == "curled"
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
