"""Turn camera frames into hand reports, gesture commands, and an annotated frame.

The engine has no user interface. A frontend calls ``process_frame`` on its
own schedule, displays the returned ``FrameResult``, and forwards user intent
through the engine's public methods.
"""

from contextlib import ExitStack
from dataclasses import dataclass

import cv2

from hand_tracking.backend.capture.camera import Camera
from hand_tracking.backend.capture.camera_status import CameraStatus
from hand_tracking.backend.engine.components import FrameOverlays, HandPipeline
from hand_tracking.backend.engine.frame_profiler import FrameProfiler
from hand_tracking.backend.gestures.gesture_config import GestureConfig
from hand_tracking.backend.gestures.hand_report import HandReport
from hand_tracking.backend.landmarker.model_asset import HandLandmarkerAsset
from hand_tracking.backend.landmarker.model_status import ModelStatus
from hand_tracking.backend.settings.settings_manager import Settings, SettingsData, SettingsValues


@dataclass
class TrackingSwitches:
    """The settings and user switches that decide whether hands are tracked."""

    enabled: bool | None = None     # "Enable hand tracking" setting
    paused: bool = False            # Pause/Resume tracking button
    commands_active: bool = False   # Debugging page visible or desktop overlay on

    def can_track(self, model_status) -> bool:
        """Detection is possible and neither the settings nor the user paused it."""
        return bool(model_status.can_detect and self.enabled and not self.paused)


@dataclass(frozen=True)
class FrameResult:
    """Everything one processed frame produced for display."""

    camera_status: CameraStatus
    model_status: ModelStatus
    hand_reports: list[HandReport]
    frame: object | None = None     # Annotated BGR image; None when the camera has none


class TrackingEngine:
    """Coordinates the camera, hand pipeline, and frame drawings."""

    def __init__(
        self, settings: Settings, camera: Camera, pipeline: HandPipeline, overlays: FrameOverlays,
    ):
        self.settings = settings
        self.camera = camera
        self.pipeline = pipeline
        self.overlays = overlays
        self.switches = TrackingSwitches()
        self.frame_profiler = FrameProfiler(enabled=bool(settings.data.profile))
        self._model_status = None
        self.apply_settings()

    @property
    def model_asset(self) -> HandLandmarkerAsset:
        return self.pipeline.tracker.asset

    def apply_settings(self) -> None:
        """Copy values from the settings object onto the running components."""
        data = self.settings.data
        previously_enabled = self.switches.enabled
        self.pipeline.apply_settings(data)
        self.switches.enabled = data.track_hands
        if previously_enabled and not data.track_hands:
            self.pipeline.gestures.suspend()
        self.frame_profiler.enabled = bool(data.profile)

    def use_settings_file(self, path: str) -> None:
        self.settings.use_file(path)
        self.apply_settings()

    def apply_changes(self, values: SettingsValues) -> SettingsData:
        """Validate, persist, and apply the submitted settings fields."""
        model_path = values.get("hand_landmarker_model_path")
        if model_path and model_path != self.settings.data.hand_landmarker_model_path:
            self.model_asset.validate_path(model_path)
        data = self.settings.update_fields(values)
        self.apply_settings()
        return data

    def apply_gesture_config(self, config: GestureConfig) -> None:
        """Apply a validated, saved gesture mapping to the running handler."""
        self.pipeline.gestures.configure(config)

    def restart_camera(self) -> None:
        self.camera.request_switch(self.camera.requested_index)

    def restart_hand_tracking(self) -> None:
        """Reset the hand pipeline without reopening the shared camera."""
        self.pipeline.restart(self.settings.data.hand_landmarker_model_path)
        self.switches.paused = False
        if self.overlays.command_overlay is not None:
            self.overlays.command_overlay.reset()

    def toggle_pause(self) -> bool:
        """Pause or resume tracking; returns whether tracking is now paused."""
        self.switches.paused = not self.switches.paused
        if self.switches.paused:
            self.pipeline.gestures.suspend()
        return self.switches.paused

    def set_commands_active(self, active: bool) -> None:
        """Commands run only while a frontend view allows them."""
        self.switches.commands_active = active
        if not active:
            self.pipeline.gestures.suspend()

    def process_frame(self, *, preview_requested: bool = False) -> FrameResult:
        """Process the latest camera frame.

        ``preview_requested`` asks for detection without invoking commands,
        for views that preview live hand data.
        """
        pipeline, overlays, switches = self.pipeline, self.overlays, self.switches
        model_status = pipeline.tracker.model_status
        if model_status != self._model_status:
            pipeline.detector.reset()
            pipeline.gestures.suspend()
            self._model_status = model_status
        can_track = switches.can_track(model_status)
        with self.frame_profiler.measure("commands.update"):
            pipeline.gestures.update(allow_repeats=can_track and switches.commands_active)

        with self.frame_profiler.measure("camera.status"):
            camera_status = self.camera.status()
        with self.frame_profiler.measure("camera.read_copy"):
            frame = self.camera.read()
        if frame is None:
            pipeline.detector.reset()
            # A failed device should leave the controls available for choosing
            # another camera rather than terminating the whole application.
            pipeline.gestures.finish_frame(set())
            return FrameResult(camera_status, model_status, [])

        hand_reports = []
        if can_track and (switches.commands_active or preview_requested):
            with self.frame_profiler.measure("tracker.prepare_submit"):
                tracking = pipeline.tracker.detect(frame)
            with self.frame_profiler.measure("landmarks.draw"):
                overlays.landmarks.draw(frame, tracking.hand_landmarks)
            with self.frame_profiler.measure("frame.flip"):
                cv2.flip(frame, 1, dst=frame)  # in place, no new allocation
            with self.frame_profiler.measure("gestures.process"):
                hand_reports = pipeline.analyze(
                    frame, tracking, invoke_commands=switches.commands_active,
                )
                overlays.draw_hand_status(frame, hand_reports)
        else:
            pipeline.detector.reset()
            with self.frame_profiler.measure("frame.flip"):
                cv2.flip(frame, 1, dst=frame)

        with self.frame_profiler.measure("gesture_path.draw"):
            overlays.gesture_paths.draw(frame, pipeline.gestures.drawing_paths)
        # Once per frame, even when no hands are visible
        with self.frame_profiler.measure("overlay.compose"):
            if overlays.command_overlay is not None:
                frame = overlays.command_overlay.draw(frame)
        return FrameResult(camera_status, model_status, hand_reports, frame)

    def finish_frame(self) -> None:
        """Close the profiler's frame and print its periodic summary."""
        fps = self.frame_profiler.finish_frame()
        if fps is None:
            return
        samples, average_ms, maximum_ms = self.pipeline.tracker.take_latency_stats()
        if samples:
            print(
                f"FPS: {fps:.1f} | detection latency "
                f"submit→result avg/max: "
                f"{average_ms:.2f}/{maximum_ms:.2f} ms"
            )
        else:
            print(f"FPS: {fps:.1f} | detection latency: no results")

    def close(self) -> None:
        # Run every cleanup even if an earlier one raises; the last registered
        # runs first: input and inference, then the camera.
        with ExitStack() as cleanup:
            cleanup.callback(self.camera.release)
            cleanup.callback(self.pipeline.close)
