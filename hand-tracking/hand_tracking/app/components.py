"""The groups of collaborators that the application coordinates.

Each record bundles components that are created, used, and closed together,
so ``Application`` receives three dependencies instead of a long list of
loosely related objects. ``main.py`` builds them at the composition root.
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from typing import TYPE_CHECKING

from hand_tracking.gestures.hand_report import HandReport

if TYPE_CHECKING:
    from hand_tracking.capture.camera import Camera
    from hand_tracking.capture.camera_preview import CameraPreview
    from hand_tracking.frame_overlays.invoker_overlay import InvokerOverlay
    from hand_tracking.frame_overlays.debug_overlay import DebugOverlay
    from hand_tracking.gestures.gesture_handler import GestureHandler
    from hand_tracking.frame_overlays.gesture_path_overlay import GesturePathOverlay
    from hand_tracking.gestures.detector import Detector
    from hand_tracking.frame_overlays.hand_drawer import HandDrawer
    from hand_tracking.landmarker.hand_tracker import HandTracker
    from hand_tracking.frame_overlays.image_overlay import ImageOverlay
    from hand_tracking.settings.settings_manager import SettingsData


@dataclass(frozen=True)
class VideoIO:
    """Where frames come from, and the window that shows the annotated result."""

    camera: Camera
    preview: CameraPreview

    def close(self) -> None:
        # Run every cleanup even if an earlier one raises.
        with ExitStack() as cleanup:
            cleanup.callback(self.camera.release)
            cleanup.callback(self.preview.close)


@dataclass(frozen=True)
class HandPipeline:
    """Turns camera frames into hand reports and gesture commands."""

    tracker: HandTracker
    detector: Detector
    gestures: GestureHandler

    def apply_settings(self, data: SettingsData) -> None:
        """Use the current detection, model, and optimistic-tracking settings."""
        self.detector.configure(data)
        self.gestures.configure_optimistic(data.optimistic_tracking)
        self.tracker.request_model(data.hand_landmarker_model_path)

    def restart(self, model_path: str) -> None:
        """Reload the model and clear gesture input, keeping the current mapping."""
        self.tracker.request_model(model_path, force=True)
        self.gestures.configure(self.gestures.config)

    def analyze(self, frame, tracking, *, invoke_commands: bool) -> list[HandReport]:
        """Classify each detected hand in a mirrored frame and handle its gesture."""
        height, width = frame.shape[:2]
        aspect = width / height
        reports = []
        for hand, handedness in zip(tracking.hand_landmarks, tracking.handedness):
            hand_name = handedness[0].category_name
            state = self.detector.update(hand, hand_name, aspect)
            gesture = self.gestures.handle(
                state, hand_name, frame_size=(width, height), invoke_commands=invoke_commands,
            )
            reports.append(HandReport(hand_name, state, gesture))
        self.gestures.finish_frame(
            {report.handedness for report in reports}, invoke_commands=invoke_commands,
        )
        return reports

    def close(self) -> None:
        # Release held keys before stopping inference.
        with ExitStack() as cleanup:
            cleanup.callback(self.tracker.close)
            cleanup.callback(self.gestures.close)


@dataclass(frozen=True)
class FrameOverlays:
    """Everything drawn onto the camera frame."""

    landmarks: HandDrawer
    hand_status: DebugOverlay
    gesture_paths: GesturePathOverlay
    invoker: InvokerOverlay
    # Built at startup but never drawn; see docs/dead_code_checklist.md.
    image: ImageOverlay | None = None

    def draw_hand_status(self, frame, reports) -> None:
        for report in reports:
            self.hand_status.update(frame, report.state)
