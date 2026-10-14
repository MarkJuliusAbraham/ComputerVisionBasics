"""Create gesture definitions independently of mapping sessions and UI widgets."""

from itertools import product
from uuid import uuid4

from .finger_classifier import finger_categories
from .hand_landmarks import FINGER_NAMES
from .gesture_config import CommandSequence, CommandStep, GestureConfig, GestureDefinition, GestureMatch
from .palm_detector import PalmPosition
from .repeating.settings import RepeatSettings


class GestureFactory:
    @staticmethod
    def create(
        current_definitions, segment_count=4, reset_match=None, *, repeat_settings=None,
    ):
        """Choose an unused pattern for a newly managed gesture."""
        fingers = FINGER_NAMES
        positions = tuple(category.value for category in finger_categories(segment_count))
        existing = [definition.match for definition in current_definitions]
        if reset_match is not None:
            existing.append(reset_match)
        for palm in (None, *(position.value for position in PalmPosition)):
            for pattern in product(positions, repeat=len(fingers)):
                match = GestureMatch(
                    palm=palm,
                    fingers={
                        finger: frozenset((position,))
                        for finger, position in zip(fingers, pattern)
                    },
                )
                if all(
                    not GestureConfig.matches_can_overlap(match, current)
                    for current in existing
                ):
                    break
            else:
                continue
            break
        else:
            raise ValueError("No gesture pattern is available outside the command and reset rules")

        existing_ids = {definition.id for definition in current_definitions}
        gesture_id = f"gesture_{uuid4().hex[:8]}"
        while gesture_id in existing_ids:
            gesture_id = f"gesture_{uuid4().hex[:8]}"
        return GestureDefinition(
            id=gesture_id,
            name="New Gesture",
            match=match,
            commands=CommandSequence((CommandStep(type="key_tap", value="a"),)),
            repeat_settings=repeat_settings if repeat_settings is not None else RepeatSettings(),
        )
