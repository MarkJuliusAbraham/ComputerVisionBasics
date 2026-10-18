"""Temporary Invoker feature observing executed keys rather than gesture IDs."""

from collections import deque
from pathlib import Path
import time

import cv2


SPELL_ICONS = {
    "qqq": "Cold_Snap_icon.webp",
    "qqw": "Ghost_Walk_icon.webp",
    "eqq": "Ice_Wall_icon.webp",
    "qww": "Tornado_icon.webp",
    "eqw": "Deafening_Blast_icon.webp",
    "eeq": "Forge_Spirit_icon.webp",
    "www": "emp.webp",
    "eww": "Alacrity_icon.webp",
    "eew": "Chaos_Meteor_icon.webp",
    "eee": "Sun_Strike_icon.webp",
}


class InvokerOverlay:
    """Own the bounded element history, icon cache, and short-lived frame drawing.

    Q/W/E retain the latest three elements; R invokes their order-independent
    spell. The stack survives invocation, just as the game's orbs do.
    """

    def __init__(self, *, clock=time.monotonic, image_dir=None):
        self._clock = clock
        self._image_dir = (
            Path(image_dir) if image_dir is not None
            else Path(__file__).parent / "images" / "invoker_spells"
        )
        self._elements = deque(maxlen=3)
        self._images = {}
        self._current_image = None
        self._expires_at = 0.0

    @property
    def elements(self) -> tuple[str, ...]:
        return tuple(self._elements)

    def reset(self) -> None:
        self._elements.clear()
        self._current_image = None
        self._expires_at = 0.0

    def on_command(self, command: str) -> None:
        """Observe released commands, including sequence and repeat steps."""
        if command in ("q", "w", "e"):
            self._elements.append(command)
        elif command == "r" and len(self._elements) == 3:
            filename = SPELL_ICONS["".join(sorted(self._elements))]
            if filename not in self._images:
                path = self._image_dir / filename
                # Missing optional assets must not break command execution.
                self._images[filename] = cv2.imread(str(path)) if path.is_file() else None
            self._current_image = self._images[filename]
            self._expires_at = self._clock() + 1.0

    def draw(self, frame):
        if self._current_image is None:
            return frame
        if self._clock() >= self._expires_at:
            self._current_image = None
            return frame
        height, width = frame.shape[:2]
        side = min(200, height, width)
        if side > 0:
            image = cv2.resize(self._current_image, (side, side))
            frame[height - side:height, width - side:width] = image
        return frame
