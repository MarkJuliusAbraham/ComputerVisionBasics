import time

from input.input_simulator import InputSimulator


class CommandExecutor:
    """Executes configured command sequences through available input adapters."""

    def __init__(self, input_simulator=None, on_command=None):
        self.input_simulator = input_simulator or InputSimulator()
        self.on_command = on_command

    def execute(self, sequence):
        executed = []
        for index, step in enumerate(sequence.steps):
            if index and sequence.delay_ms_between_steps:
                time.sleep(sequence.delay_ms_between_steps / 1000)
            if step.type == "key_tap":
                self.input_simulator.tap(step.value)
            else:
                raise ValueError(f"Unsupported command type: {step.type}")
            executed.append(step.value)
            if self.on_command:
                self.on_command(step.value)
        return tuple(executed)
