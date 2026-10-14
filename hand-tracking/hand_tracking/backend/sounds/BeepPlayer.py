import numpy as np
import pygame

pygame.mixer.init(frequency=44100, size=-16, channels=1)

_rate, _, _channels = pygame.mixer.get_init()
_t = np.linspace(0, 0.12, int(_rate * 0.12), endpoint=False)
_tone = np.sin(2 * np.pi * 660 * _t) * np.minimum(_t / 0.008, 1) * np.exp(-_t * 30)
_samples = (_tone / np.abs(_tone).max() * 32767).astype(np.int16)

if _channels == 2:
    _samples = np.column_stack((_samples, _samples))

_sound = pygame.sndarray.make_sound(_samples)
_sound.set_volume(0.3)


class BeepPlayer:
    @staticmethod
    def beep():
        _sound.play()