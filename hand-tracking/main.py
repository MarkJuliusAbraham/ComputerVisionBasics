import os

from contextlib import ExitStack

from hand_tracking.backend.capture.camera import Camera
from hand_tracking.backend.common.diagnostics import RuntimeDiagnostics
from hand_tracking.backend.engine.components import FrameOverlays, HandPipeline
from hand_tracking.backend.engine.engine import TrackingEngine
from hand_tracking.backend.frame_overlays.debug_overlay import DebugOverlay
from hand_tracking.backend.frame_overlays.gesture_path_overlay import GesturePathOverlay
from hand_tracking.backend.frame_overlays.hand_drawer import HandDrawer
from hand_tracking.backend.frame_overlays.image_overlay import ImageOverlay
from hand_tracking.backend.frame_overlays.invoker_overlay import InvokerOverlay
from hand_tracking.backend.gestures.detector import Detector
from hand_tracking.backend.gestures.gesture_handler import GestureHandler
from hand_tracking.backend.landmarker.hand_tracker import HandTracker
from hand_tracking.backend.settings.settings_manager import Settings
from hand_tracking.frontend.application import Application
from hand_tracking.frontend.camera_preview import CameraPreview
from hand_tracking.frontend.components.dpi import enable_dpi_awareness
from hand_tracking.frontend.core.native_window_style import FixedNativeWindowStyle

def open_camera(startup: ExitStack) -> Camera:
    camera = Camera()
    startup.callback(camera.release)
    return camera


def open_preview(startup: ExitStack) -> CameraPreview:
    preview = CameraPreview(window_style=FixedNativeWindowStyle())
    startup.callback(preview.close)
    return preview


def start_hand_pipeline(startup: ExitStack, settings: Settings, *, on_command=None) -> HandPipeline:
    tracker = HandTracker(model_path=settings.data.hand_landmarker_model_path)
    startup.callback(tracker.close)
    gestures = GestureHandler(on_command=on_command)
    startup.callback(gestures.close)
    return HandPipeline(tracker, Detector(settings.data), gestures)


def create_frame_overlays(*, command_overlay=None) -> FrameOverlays:
    landmarks = HandDrawer()
    return FrameOverlays(
        landmarks=landmarks,
        hand_status=DebugOverlay(),
        gesture_paths=GesturePathOverlay(landmarks),
        command_overlay=command_overlay,
        image=ImageOverlay(),
    )


def build_application(settings: Settings, *, heartbeat=None) -> Application:
    """Create every component; close the ones already started if one fails."""
    with ExitStack() as startup:
        camera = open_camera(startup)
        preview = open_preview(startup)
        # Temporary Invoker feature: remove this construction and the two
        # optional connections below to run without its element stack/display.
        invoker = InvokerOverlay()
        pipeline = start_hand_pipeline(startup, settings, on_command=invoker.on_command)
        engine = TrackingEngine(
            settings, camera, pipeline, create_frame_overlays(command_overlay=invoker),
        )
        app = Application(engine, preview, heartbeat=heartbeat)
        startup.pop_all()  # Application owns cleanup after construction.
    return app


def main():
    enable_dpi_awareness()
    with RuntimeDiagnostics() as diagnostics:
        settings = Settings()
        while True:
            diagnostics.heartbeat()
            settings.load()
            app = build_application(settings, heartbeat=diagnostics.heartbeat)
            app.run()

            if not app.restart_requested:
                break


if __name__ == "__main__":
    main()
