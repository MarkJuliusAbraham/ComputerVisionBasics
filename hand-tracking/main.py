import os

from contextlib import ExitStack

from app_components import FrameOverlays, HandPipeline, VideoIO
from application import Application
from camera import Camera
from camera_preview import CameraPreview
from custom_overlay.invoker_overlay import InvokerOverlay
from debug_overlay import DebugOverlay
from gestures.detector import Detector
from gesture_handler import GestureHandler
from gesture_path_overlay import GesturePathOverlay
from hand_drawer import HandDrawer
from hand_tracker import HandTracker
from image_module.image_overlay import ImageOverlay
from settings.settings_manager import Settings
from gui_tkinter.components.dpi import enable_dpi_awareness
from gui_tkinter.core.native_window_style import FixedNativeWindowStyle


def open_video(startup: ExitStack) -> VideoIO:
    camera = Camera()
    startup.callback(camera.release)
    preview = CameraPreview(window_style=FixedNativeWindowStyle())
    startup.callback(preview.close)
    return VideoIO(camera, preview)


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
        video = open_video(startup)
        invoker = InvokerOverlay()
        pipeline = start_hand_pipeline(startup, settings, invoker)
        app = Application(settings, video, pipeline, create_frame_overlays(invoker))
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
