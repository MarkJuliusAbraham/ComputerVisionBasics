import os

from contextlib import ExitStack

from hand_tracking.backend.capture.camera import Camera
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


def start_hand_pipeline(startup: ExitStack, settings: Settings, invoker: InvokerOverlay) -> HandPipeline:
    tracker = HandTracker(model_path=settings.data.hand_landmarker_model_path)
    startup.callback(tracker.close)
    # Each released command key is reported to the Invoker overlay.
    gestures = GestureHandler(invoker)
    startup.callback(gestures.close)
    return HandPipeline(tracker, Detector(settings.data), gestures)


def create_frame_overlays(invoker: InvokerOverlay) -> FrameOverlays:
    landmarks = HandDrawer()
    return FrameOverlays(
        landmarks=landmarks,
        hand_status=DebugOverlay(),
        gesture_paths=GesturePathOverlay(landmarks),
        invoker=invoker,
        image=ImageOverlay(),
    )


def build_application(settings: Settings) -> Application:
    """Create every component; close the ones already started if one fails."""
    with ExitStack() as startup:
        camera = open_camera(startup)
        preview = open_preview(startup)
        invoker = InvokerOverlay()
        pipeline = start_hand_pipeline(startup, settings, invoker)
        engine = TrackingEngine(settings, camera, pipeline, create_frame_overlays(invoker))
        app = Application(engine, preview)
        startup.pop_all()  # Application owns cleanup after construction.
    return app


def main():
    enable_dpi_awareness()
    settings = Settings()
    while True:
        settings.load()
        app = build_application(settings)
        app.run()

        if not app.restart_requested:
            break


if __name__ == "__main__":
    main()
