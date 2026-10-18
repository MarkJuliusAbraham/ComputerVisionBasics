from dataclasses import dataclass

from .geometry import palm_size
from .finger_classifier import FingerClassifier, FingerState, FingerPosition
from .finger_hysteresis import FingerHysteresis
from .hand_landmarks import Landmark, point
from .palm_detector import PalmDetector, PalmPosition
from .tracking.path import Point


@dataclass(frozen=True)
class GestureState:
    palm: PalmPosition
    fingers: dict[str, FingerState]
    wrist: Point | None = None
    palm_size: float | None = None  # Fraction of the frame width

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
        self._finger_hysteresis = FingerHysteresis(
            self._finger_classifier.thresholds, self._finger_classifier.categories,
            settings.finger_hysteresis_margin_degrees if settings.finger_hysteresis_enabled else 0,
        )

    def reset(self):
        self._finger_hysteresis.reset()

    def finish_frame(self, present_hands):
        self._finger_hysteresis.finish_frame(present_hands)

    def update(self, hand, handedness: str, aspect: float = 1.0) -> GestureState:
        """Classify one hand; ``aspect`` is the analyzed frame's width/height."""
        return GestureState(
            palm=self._palm_detector.detect(hand, handedness, aspect),
            fingers=self._finger_hysteresis.apply(
                handedness, self._finger_classifier.classify_all(hand, aspect),
            ),
            wrist=point(hand[Landmark.WRIST]),
            palm_size=palm_size(
                hand[Landmark.WRIST], hand[Landmark.MIDDLE_MCP],
                hand[Landmark.INDEX_MCP], hand[Landmark.PINKY_MCP], aspect,
            ),
        )
