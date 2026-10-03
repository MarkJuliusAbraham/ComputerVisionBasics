from pycaw.pycaw import AudioUtilities


class VolumeController:
    def __init__(self):
        self._device = AudioUtilities.GetSpeakers()
        self._volume = self._device.EndpointVolume

    @property
    def level(self) -> float:
        """Return the current volume from 0.0 to 1.0."""
        return self._volume.GetMasterVolumeLevelScalar()

    @level.setter
    def level(self, value: float):
        """Set the volume, clamping it between 0.0 and 1.0."""
        value = max(0.0, min(1.0, value))
        self._volume.SetMasterVolumeLevelScalar(value, None)

    def set_percentage(self, percentage: float):
        """Set volume from 0 to 100, clamping outside values."""
        self.level = percentage / 100


# volume = VolumeController()
#
# volume.set_percentage(50)
#
# print(f"Volume: {volume.level * 100:.0f}%")
