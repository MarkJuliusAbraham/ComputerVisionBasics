"""One live hand report shared by debugging widgets and settings previews."""

from __future__ import annotations

from dataclasses import dataclass

from hand_tracking.gestures.hand_report import HandReport


@dataclass(frozen=True)
class LiveHandData:
    records: tuple[HandReport, ...] = ()
    enabled: bool = True
    paused: bool = False
    blocking_reason: str = ""

    @property
    def tracking_status(self):
        if not self.enabled:
            return "Tracking disabled"
        if self.blocking_reason:
            return self.blocking_reason
        return "Tracking paused" if self.paused else "Tracking active"

    @property
    def preview_fingers(self):
        return self.records[0].state.fingers if self.records else None

    @property
    def preview_status(self):
        if not self.enabled or self.blocking_reason or self.paused:
            return self.tracking_status
        if not self.records:
            return "No hand detected"
        return f"Live data · {self.records[0].handedness} hand"

    @property
    def by_hand(self):
        return {record.handedness: record for record in self.records}
