from dataclasses import dataclass

from .finger_classifier import FingerClassifier, FingerState, FingerPosition
from .palm_detector import PalmDetector, PalmPosition
from .tracking.path import Point


@dataclass(frozen=True)
class GestureState:
    palm: PalmPosition
    fingers: dict[str, FingerState]
    wrist: Point | None = None

    @property
    def fingers_up(self) -> int:
        return sum(
            finger.position == FingerPosition.STRAIGHT
            for finger in self.fingers.values()
        )

class Detector:
    def __init__(self, settings):
        self._palm_detector = PalmDetector()
        self.configure(settings)

    def configure(self, settings):
        self._finger_classifier = FingerClassifier(
            settings.finger_classification_thresholds,
            settings.finger_deviation_calculation,
            settings.finger_segment_count,
        )

    def update(self, hand, handedness: str) -> GestureState:
        fingers = self._finger_classifier.classify_all(hand)

        palm = self._palm_detector.detect(
            hand,
            handedness,
        )

        state = GestureState(
            palm=palm,
            fingers=fingers,
            wrist=(hand[0].x, hand[0].y, hand[0].z),
        )
        return state
