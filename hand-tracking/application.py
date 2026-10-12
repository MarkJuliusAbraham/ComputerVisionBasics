import time
import cv2
from contextlib import ExitStack

from gui_tkinter.control_window import ControlWindow as Gui
from gui_tkinter.core.state import ControlCallbacks, ControlWindowContext, PanelSet
from gui_tkinter.mapping_panel import MappingPanel
from gui_tkinter.main_panel import MainPanel
from gui_tkinter.settings_panel import SettingsPanel
from frame_profiler import FrameProfiler
from gesture_path_overlay import GesturePathOverlay


class Application:
    """Coordinates the application components."""

    def __init__(
        self,
        camera,
        tracker,
        drawer,
        debug_overlay,
        detector,
        gesture_handler,
        image_overlay,
        invoker_overlay,
        settings,
    ):
        self.profile = None
        self.theme = None
        self.track_hands = None
        self.camera = camera
        self.tracker = tracker
        self.drawer = drawer
        self.debug_overlay = debug_overlay
        self.detector = detector
        self.gesture_handler = gesture_handler
        self.gesture_path_overlay = GesturePathOverlay(drawer)
        self.image_overlay = image_overlay
        self.invoker_overlay = invoker_overlay
        self.settings = settings
        self.frame_profiler = FrameProfiler(enabled=bool(settings.data.profile))
        self.apply_settings()

        self.running = True
        self.restart_requested = False
        self.tracking_paused = False
        self._tracking_tab_active = True
        self._camera_ui_state = None
        self._gesture_display_updated = 0.0
        self._latest_hand_states = []
        panels = PanelSet(
            main=MainPanel(),
            settings=SettingsPanel(),
            mapping=MappingPanel(on_saved=self.apply_gesture_config),
        )
        self.panels = panels
        callbacks = ControlCallbacks(
            on_restart=self.request_restart,
            on_close=self.request_quit,
            on_settings_path=self.load_settings_file,
            on_apply=self.apply_changes,
            on_camera_switch=self.camera.request_switch,
            on_toggle_tracking=self.toggle_tracking,
            on_tracking_tab_active=self.set_tracking_tab_active,
        )
        context = ControlWindowContext(
            settings=settings,
            callbacks=callbacks,
            panels=panels,
            camera_index=self.camera.requested_index,
        )
        self.gui = Gui(context)


    def apply_settings(self):
        """Copy values from the settings object onto the app."""
        self.detector.configure(self.settings.data)
        self.track_hands = self.settings.data.track_hands
        self.profile = self.settings.data.profile
        self.frame_profiler.enabled = bool(self.profile)
        self.theme = self.settings.data.theme

    def load_settings_file(self, path):
        """Called when the user browses to a different file."""
        self.settings.use_file(path)
        self.apply_settings()
        self.panels.settings.show_settings(self.settings)
        self.panels.main.set_display(
            self.settings.data.theme,
            self.settings.data.finger_classification_thresholds[-1],
        )

    def apply_changes(self, data):
        """Called when the user clicks Apply in the GUI."""
        self.settings.update(data)
        self.apply_settings()
        self.panels.main.set_display(
            data.theme, data.finger_classification_thresholds[-1]
        )

    def apply_gesture_config(self, config):
        """Apply a validated, saved gesture mapping to the running handler."""
        self.gesture_handler.configure(config)

    def request_restart(self):
        if not self.running:
            return
        # Restart the tracking pipeline in place. Dear PyGui owns a native
        # viewport, so rebuilding the ControlWindow here creates duplicate
        # windows. Reopening the active camera and clearing detector state
        # gives Restart its expected effect while preserving the one UI.
        self.gesture_handler.configure(self.gesture_handler.config)
        self.camera.request_switch(self.camera.requested_index)
        self._camera_ui_state = None
        self._latest_hand_states = []
        self._gesture_display_updated = 0.0
        self.tracking_paused = False
        self.panels.main.set_tracking_paused(False)
        self.invoker_overlay.spell_stack.clear()
        self.invoker_overlay.current_image = None
        self.invoker_overlay.image_expiry = 0

    def request_quit(self):
        self.running = False
        self.gui.quit()

    def toggle_tracking(self):
        self.tracking_paused = not self.tracking_paused
        self.panels.main.set_tracking_paused(self.tracking_paused)

    def set_tracking_tab_active(self, active):
        """Suspend hand detection while the Main tab is not visible."""
        self._tracking_tab_active = active

    def run(self):
        try:
            self.gui.after(0, self._process_frame)
            self.gui.run()
        except KeyboardInterrupt:
            self.running = False
        finally:
            self.close()

    def _process_frame(self):
        """Process one frame, then yield to the control window's event loop."""
        if not self.running:
            return

        try:
            self._process_frame_work()
        finally:
            fps = self.frame_profiler.finish_frame()
            if fps is not None:
                samples, average_ms, maximum_ms = self.tracker.take_latency_stats()
                if samples:
                    print(
                        f"FPS: {fps:.1f} | detection latency "
                        f"submit→result avg/max: "
                        f"{average_ms:.2f}/{maximum_ms:.2f} ms"
                    )
                else:
                    print(f"FPS: {fps:.1f} | detection latency: no results")

    def _process_frame_work(self):
        """Run and measure the work for one event-loop frame."""
        with self.frame_profiler.measure("commands.update"):
            self.gesture_handler.update(
                allow_repeats=self.track_hands and not self.tracking_paused and self._tracking_tab_active
            )

        with self.frame_profiler.measure("camera.status"):
            camera_state = self.camera.status()
        if camera_state != self._camera_ui_state:
            with self.frame_profiler.measure("ui.camera_status"):
                self.panels.main.update_camera_state(*camera_state)
            self._camera_ui_state = camera_state
        with self.frame_profiler.measure("camera.read_copy"):
            frame = self.camera.read()
        if frame is None:
            # A failed device should leave the controls available for choosing
            # another camera rather than terminating the whole application.
            with self.frame_profiler.measure("opencv.wait_key"):
                cv2.waitKey(1)
            self.gui.after(10, self._process_frame)
            return

        preview_active = self.panels.settings.tracking_preview_active
        if self.track_hands and not self.tracking_paused and (self._tracking_tab_active or preview_active):
            with self.frame_profiler.measure("tracker.prepare_submit"):
                tracking = self.tracker.detect(frame)
            with self.frame_profiler.measure("landmarks.draw"):
                self.drawer.draw(frame, tracking.hand_landmarks)
            with self.frame_profiler.measure("frame.flip"):
                cv2.flip(frame, 1, dst=frame)  # in place, no new allocation
            with self.frame_profiler.measure("gestures.process"):
                self._latest_hand_states = self.process_hands(
                    frame, tracking, invoke_commands=self._tracking_tab_active
                )
        else:
            with self.frame_profiler.measure("frame.flip"):
                cv2.flip(frame, 1, dst=frame)
            self._latest_hand_states = []

        with self.frame_profiler.measure("gesture_path.draw"):
            self.gesture_path_overlay.draw(frame, self.gesture_handler.drawing_path)

        now = time.monotonic()
        if now - self._gesture_display_updated >= 0.1:
            with self.frame_profiler.measure("ui.gesture_display"):
                self.panels.main.update_gesture_display(
                    self._latest_hand_states,
                    enabled=self.track_hands,
                    paused=self.tracking_paused,
                )
                main_panel = self.panels.main
                self.panels.settings.set_preview_data(
                    main_panel.preview_fingers,
                    main_panel.preview_status,
                )
            self._gesture_display_updated = now

        # Once per frame, even when no hands are visible
        with self.frame_profiler.measure("overlay.compose"):
            frame = self.invoker_overlay.handleDisplay(frame)
        with self.frame_profiler.measure("opencv.imshow"):
            cv2.imshow("Hand Tracking", frame)
        with self.frame_profiler.measure("opencv.wait_key"):
            cv2.waitKey(1)

        self.gui.after(1, self._process_frame)

    def process_hands(self, frame, tracking, invoke_commands=True):
        hand_states = []
        for hand, handedness in zip(tracking.hand_landmarks, tracking.handedness):
            classification = handedness[0]
            hand_name = classification.category_name
            state = self.detector.update(hand, hand_name)
            self.debug_overlay.update(frame, state)

            command = self.gesture_handler.handle(
                state,
                hand_name,
                frame_size=(frame.shape[1], frame.shape[0]),
            ) if invoke_commands else None
            hand_states.append({
                "handedness": hand_name,
                "state": state,
                "command": command,
            })
        return hand_states


    def close(self):
        self.running = False
        # Run every cleanup even if an earlier resource raises while closing.
        with ExitStack() as cleanup:
            cleanup.callback(cv2.destroyAllWindows)
            cleanup.callback(self.tracker.close)
            cleanup.callback(self.camera.release)
            cleanup.callback(self.gui.close)
            cleanup.callback(self.gesture_handler.close)
