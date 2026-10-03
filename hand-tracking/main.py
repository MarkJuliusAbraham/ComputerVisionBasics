from application import Application
from camera import Camera
from custom_overlay.invoker_overlay import InvokerOverlay
from debug_overlay import DebugOverlay
from gestures.detector import Detector
from gesture_handler import GestureHandler
from hand_drawer import HandDrawer
from hand_tracker import HandTracker
from image_module.image_overlay import ImageOverlay



def main():
    camera = Camera()
    tracker = HandTracker()
    drawer = HandDrawer()
    debug_overlay = DebugOverlay()
    detector = Detector()
    invoker_overlay = InvokerOverlay()
    gesture_handler = GestureHandler(invoker_overlay)
    image_overlay = ImageOverlay()

    app = Application(
        camera=camera,
        tracker=tracker,
        drawer=drawer,
        debug_overlay=debug_overlay,
        detector=detector,
        gesture_handler=gesture_handler,
        image_overlay=image_overlay,
        invoker_overlay=invoker_overlay,
    )

    app.run()


if __name__ == "__main__":
    main()
