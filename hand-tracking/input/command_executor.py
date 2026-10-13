from collections import deque
from dataclasses import dataclass
import time
import random
from typing import Callable

from input.input_simulator import InputSimulator
from input.command_modifier import CommandModifier


@dataclass
class _SequenceTask:
    steps: tuple
    delay_seconds: float
    index: int = 0
    action: str = "press"
    due_at: float = 0.0
    repeats_remaining: int = 0
    modifier: CommandModifier = CommandModifier()
    is_repeat: bool = False
    on_repeat: Callable[[], None] | None = None
    on_start: Callable[[], None] | None = None


class CommandExecutor:
    """Schedules command key actions without blocking the application loop."""

    KEY_HOLD_SECONDS = 0.05

    def __init__(self, input_simulator=None, on_command=None, *, random_uniform=None):
        self.input_simulator = input_simulator or InputSimulator()
        self.on_command = on_command
        self.random_uniform = random_uniform if random_uniform is not None else random.uniform
        self._pending = deque()
        self._active = None

    def execute(self, sequence, *, modifier=None, on_repeat=None, on_start=None):
        if not sequence.steps:
            return
        if any(step.type != "key_tap" for step in sequence.steps):
            raise ValueError("Unsupported command type in sequence")
        if modifier is not None and not isinstance(modifier, CommandModifier):
            raise ValueError("Command modifier must be a CommandModifier object")
        task = _SequenceTask(
            steps=sequence.steps,
            delay_seconds=sequence.delay_ms_between_steps / 1000,
            repeats_remaining=modifier.repeat_count if modifier is not None else 0,
            modifier=modifier if modifier is not None else CommandModifier(),
            on_repeat=on_repeat,
            on_start=on_start,
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
                if task.is_repeat and task.index == 0 and task.on_repeat is not None:
                    task.on_repeat()
                elif not task.is_repeat and task.index == 0 and task.on_start is not None:
                    task.on_start()
                return

            self.input_simulator.release(step.value)
            if self.on_command:
                self.on_command(step.value)
            task.index += 1
            if task.index >= len(task.steps):
                if task.repeats_remaining:
                    task.repeats_remaining -= 1
                    task.index = 0
                    task.action = "press"
                    task.is_repeat = True
                    task.due_at = now + task.modifier.next_delay_seconds(self.random_uniform)
                    continue
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
