from dataclasses import dataclass

from .finger_classifier import FingerClassifier, FingerState, FingerPosition
from .gesture_detector import GestureDetector, Pinching
from .palm_detector import PalmDetector, PalmPosition


@dataclass(frozen=True)
class GestureState:
    gesture: Pinching | None
    palm: PalmPosition
    fingers: dict[str, FingerState]

    @property
    def fingers_up(self) -> int:
        return sum(
            finger.position == FingerPosition.STRAIGHT
            for finger in self.fingers.values()
        )

class Detector:
    def __init__(self, settings):
        self._palm_detector = PalmDetector()
        self._previous_gestures: dict[str, Pinching | None] = {}
        self.configure(settings)

    def configure(self, settings):
        self._finger_classifier = FingerClassifier(
            settings.finger_classification_thresholds,
            settings.finger_deviation_calculation,
            settings.finger_segment_count,
        )
        self._gesture_detector = GestureDetector(
            settings.pinch_distance_threshold,
            settings.pinch_release_factor,
        )

    def update(self, hand, handedness: str) -> GestureState:
        fingers = self._finger_classifier.classify_all(hand)

        palm = self._palm_detector.detect(
            hand,
            handedness,
        )

        previous_gesture = self._previous_gestures.get(
            handedness
        )

        gesture = self._gesture_detector.detect(
            hand,
            fingers,
            previous_gesture,
        )

        state = GestureState(
            gesture=gesture,
            palm=palm,
            fingers=fingers,
        )

        self._previous_gestures[handedness] = gesture

        return state
