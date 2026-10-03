from pynput.keyboard import Controller


class InputSimulator:
    def __init__(self):
        self._keyboard = Controller()

    def press(self, key):
        self._keyboard.press(key)

    def release(self, key):
        self._keyboard.release(key)

    def tap(self, key):
        self._keyboard.press(key)
        self._keyboard.release(key)
