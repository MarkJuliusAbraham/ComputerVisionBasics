from collections import deque
from dataclasses import dataclass
import time

from input.input_simulator import InputSimulator


@dataclass
class _SequenceTask:
    steps: tuple
    delay_seconds: float
    index: int = 0
    action: str = "press"
    due_at: float = 0.0


class CommandExecutor:
    """Schedules command key actions without blocking the application loop."""

    KEY_HOLD_SECONDS = 0.05

    def __init__(self, input_simulator=None, on_command=None):
        self.input_simulator = input_simulator or InputSimulator()
        self.on_command = on_command
        self._pending = deque()
        self._active = None

    def execute(self, sequence):
        if not sequence.steps:
            return
        if any(step.type != "key_tap" for step in sequence.steps):
            raise ValueError("Unsupported command type in sequence")
        task = _SequenceTask(
            steps=sequence.steps,
            delay_seconds=sequence.delay_ms_between_steps / 1000,
        )
        self._pending.append(task)
        self.update()

    def update(self, now=None):
        """Run due key actions; call regularly from the owning event loop."""
        now = time.monotonic() if now is None else now
        while True:
            if self._active is None:
                if not self._pending:
                    return
                self._active = self._pending.popleft()
                self._active.due_at = now

            task = self._active
            if now < task.due_at:
                return
            step = task.steps[task.index]

            if task.action == "press":
                self.input_simulator.press(step.value)
                task.action = "release"
                task.due_at = now + self.KEY_HOLD_SECONDS
                return

            self.input_simulator.release(step.value)
            if self.on_command:
                self.on_command(step.value)
            task.index += 1
            if task.index >= len(task.steps):
                self._active = None
                continue
            task.action = "press"
            task.due_at = now + task.delay_seconds

    def clear(self):
        """Cancel pending sequences and release a key if one is held."""
        if self._active is not None and self._active.action == "release":
            step = self._active.steps[self._active.index]
            self.input_simulator.release(step.value)
        self._active = None
        self._pending.clear()
