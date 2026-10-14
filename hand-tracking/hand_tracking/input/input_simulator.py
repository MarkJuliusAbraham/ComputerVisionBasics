from pynput.keyboard import Controller


class InputSimulator:
    def __init__(self):
        self._keyboard = Controller()

    def press(self, key):
        self._keyboard.press(key)

    def release(self, key):
        self._keyboard.release(key)
