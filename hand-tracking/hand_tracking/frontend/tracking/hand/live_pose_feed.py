"""Let editing views borrow live hand reports while they need them."""

from __future__ import annotations

from typing import Callable, Sequence

from hand_tracking.backend.gestures.hand_report import HandReport

PoseListener = Callable[[Sequence[HandReport]], None]


class LivePoseFeed:
    """Publish hand reports to subscribers; any subscriber requests detection."""

    def __init__(self) -> None:
        self._listeners: list[PoseListener] = []

    @property
    def requested(self) -> bool:
        return bool(self._listeners)

    def subscribe(self, listener: PoseListener) -> Callable[[], None]:
        """Start receiving reports; call the returned function to stop."""
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def publish(self, records: Sequence[HandReport]) -> None:
        for listener in tuple(self._listeners):
            listener(records)
