"""Build the overlay picture: the hand stats, optionally below the camera picture."""

from __future__ import annotations

import time

import cv2
from PIL import Image, ImageColor

from hand_tracking.backend.settings.overlay_settings import OverlaySettings
from hand_tracking.frontend.components.theme import ThemeMetrics

from ..debug_panel.live_hand_data import LiveHandData
from .renderer import HandOverlayRenderer

# Overlay widths in unscaled pixels when the camera is shown; the stats panel
# is drawn at full size and scaled down to match the camera.
WIDTHS = {"Small": 260, "Medium": 360, "Large": 480}
CAMERA_INTERVAL_SECONDS = 1 / 30
PLACEHOLDER_ASPECT = 9 / 16


class OverlayComposer:
    """Cache the stats panel and stack the latest camera frame above it.

    The stats only change with the hand report, while the camera changes every
    frame, so the panel is re-rendered only when its inputs change.
    """

    def __init__(
        self, renderer: HandOverlayRenderer, appearance: ThemeMetrics, *,
        interval_seconds: float = CAMERA_INTERVAL_SECONDS, clock=time.monotonic,
    ) -> None:
        self.renderer = renderer
        self.appearance = appearance
        self.interval_seconds = interval_seconds
        self.clock = clock
        self._frame = None
        self._frame_at: float | None = None
        self._stats: Image.Image | None = None
        self._stats_key = None
        self._stats_data = None

    def offer_frame(self, frame) -> bool:
        """Keep ``frame`` if a camera redraw is due; returns whether to redraw."""
        now = self.clock()
        if frame is None or (self._frame_at is not None and now - self._frame_at < self.interval_seconds):
            return False
        self._frame, self._frame_at = frame, now
        return True

    def forget_frame(self) -> None:
        self._frame = self._frame_at = None

    def compose(
        self, data: LiveHandData, preferences: OverlaySettings, *, opacity: float, max_deviation: float,
    ) -> Image.Image:
        stats = self._stats_image(data, preferences, opacity, max_deviation)
        if not preferences.shows_camera:
            return stats
        width = self.appearance.pixels(WIDTHS[preferences.size])
        if stats.width != width:
            stats = stats.resize(
                (width, max(1, round(stats.height * width / stats.width))), Image.Resampling.LANCZOS,
            )
        camera = self._camera_image(width)
        gap = self.appearance.pixels(4)
        image = Image.new("RGBA", (width, camera.height + gap + stats.height))
        image.paste(camera, (0, 0))
        image.alpha_composite(stats, (0, camera.height + gap))
        return image

    def _stats_image(self, data, preferences, opacity, max_deviation) -> Image.Image:
        # A new report is a new object, so identity is enough to detect it.
        key = (preferences.style, opacity, max_deviation, self.appearance.scale)
        if data is not self._stats_data or key != self._stats_key or self._stats is None:
            self._stats = self.renderer.render(
                data, style=preferences.style, opacity=opacity, max_deviation=max_deviation,
            )
            self._stats_data, self._stats_key = data, key
        return self._stats

    def _camera_image(self, width: int) -> Image.Image:
        if self._frame is None:
            # Until the first frame arrives, hold the camera's place.
            surface = ImageColor.getrgb(self.appearance.colors.palette.surface)
            return Image.new("RGBA", (width, round(width * PLACEHOLDER_ASPECT)), (*surface, 255))
        height, frame_width = self._frame.shape[:2]
        size = (width, max(1, round(height * width / frame_width)))
        resized = cv2.resize(self._frame, size, interpolation=cv2.INTER_AREA)
        return Image.fromarray(cv2.cvtColor(resized, cv2.COLOR_BGR2RGBA))
