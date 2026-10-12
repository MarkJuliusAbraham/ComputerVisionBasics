"""Small scheduler used by the Dear PyGui control loop.

Keeping scheduling separate from rendering makes camera and command callbacks
independent of the UI's render cadence and gives the loop one focused owner for
queued work.
"""

from dataclasses import dataclass, field
import time


@dataclass
class CallbackScheduler:
    """Run callbacks once after their requested delay."""

    _entries: list[tuple[float, object]] = field(default_factory=list)

    def schedule(self, delay_ms, callback):
        deadline = time.monotonic() + max(0, delay_ms) / 1000.0
        self._entries.append((deadline, callback))

    def pop_due(self, now=None):
        now = time.monotonic() if now is None else now
        due = [entry for entry in self._entries if entry[0] <= now]
        self._entries = [entry for entry in self._entries if entry[0] > now]
        return due

    def next_deadline(self, default):
        return min((deadline for deadline, _ in self._entries), default=default)

    def clear(self):
        self._entries.clear()
