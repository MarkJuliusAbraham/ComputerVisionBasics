from pynput.keyboard import Controller
import time
class InputSimulator:
    def __init__(self):
        self._keyboard = Controller()

    def press(self, key):
        self._keyboard.press(key)

    def release(self, key):
        self._keyboard.release(key)

    def tap(self, key, hold=0.05):
        self._keyboard.press(key)
        time.sleep(hold)  # 10 ms, about a third of a frame
        self._keyboard.release(key)