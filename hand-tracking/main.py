import os

from contextlib import ExitStack

from application import Application
from camera import Camera
from camera_preview import CameraPreview
from custom_overlay.invoker_overlay import InvokerOverlay
from debug_overlay import DebugOverlay
from gestures.detector import Detector
from gesture_handler import GestureHandler
from hand_drawer import HandDrawer
from hand_tracker import HandTracker
from image_module.image_overlay import ImageOverlay
from settings.settings_manager import Settings
from gui_tkinter.components.dpi import enable_dpi_awareness
from gui_tkinter.core.native_window_style import FixedNativeWindowStyle

def main():
    enable_dpi_awareness()
    settings = Settings()
    while True:
        settings.load()

        with ExitStack() as startup:
            camera = Camera()
            startup.callback(camera.release)
            tracker = HandTracker(model_path=settings.data.hand_landmarker_model_path)
            startup.callback(tracker.close)
            drawer = HandDrawer()
            debug_overlay = DebugOverlay()
            detector = Detector(settings.data)
            invoker_overlay = InvokerOverlay()
            gesture_handler = GestureHandler(invoker_overlay)
            startup.callback(gesture_handler.close)
            image_overlay = ImageOverlay()
            preview = CameraPreview(window_style=FixedNativeWindowStyle())
            startup.callback(preview.close)

            app = Application(
                camera=camera,
                tracker=tracker,
                drawer=drawer,
                debug_overlay=debug_overlay,
                detector=detector,
                gesture_handler=gesture_handler,
                image_overlay=image_overlay,
                invoker_overlay=invoker_overlay,
                settings=settings,
                preview=preview,
            )
            startup.pop_all()  # Application owns cleanup after construction.

        app.run()

        if not app.restart_requested:
            break


if __name__ == "__main__":
    main()
