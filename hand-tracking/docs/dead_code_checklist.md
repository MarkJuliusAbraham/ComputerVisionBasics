# Dead code checklist

Code that is never called, or whose result is never used. All of it is still
in the codebase. Tick an item once it has been removed, wired up, or kept on
purpose.

Line numbers are from the October 2026 refactor and may drift.

## Startup and application loop

- [ ] **Unused image overlay.** `create_frame_overlays` (`main.py:45`) builds
      `ImageOverlay()`, which reads `hand_tracking/frame_overlays/images/absolute_cinema.jpg`
      from disk and prints a message at every startup. It is stored as
      `FrameOverlays.image` (`hand_tracking/app/components.py:96`) and never drawn.
      Files: `hand_tracking/frame_overlays/image_overlay.py`, `main.py`, `hand_tracking/app/components.py`.
- [ ] **Restart loop that never repeats.** `Application.restart_requested`
      (`hand_tracking/app/application.py:70`) is set to `False` and never changes, so the
      `while True` loop in `main.py:63` always runs exactly once. The Restart
      button calls `request_restart`, which resets the pipeline in place.
      `settings.load()` at the top of that loop repeats the load already done by
      `Settings()`.
- [ ] **Unused import.** `import os` in `main.py:1`.
- [ ] **Unread theme name.** `Application.theme` (`hand_tracking/app/application.py:64`, set at
      `:113`) is written on every settings change and never read. The control
      window applies the theme from `SettingsData` directly.
- [ ] **No-op frame profiler stages.** `FrameProfiler.measure`
      (`hand_tracking/app/frame_profiler.py:27`) yields without measuring. It wraps 13 blocks in
      the frame loop in `hand_tracking/app/application.py`. Either measure the stages or remove the
      wrappers.

## Camera

- [ ] **Unused properties.** `Camera.switching` (`hand_tracking/capture/camera.py:28`) and
      `Camera.cap` (`hand_tracking/capture/camera.py:37`) have no callers. The UI reads
      `CameraStatus.is_switching` instead.
- [ ] **Unread aspect ratio.** `Camera.aspect` (`hand_tracking/capture/camera.py:11`, updated at
      `hand_tracking/capture/camera.py:91`) used to be read by `hand_tracking/gestures/geometry.py` as a hidden
      global. Detection now receives the analyzed frame's aspect ratio from
      `HandPipeline.analyze`, so nothing reads this value.

## Invoker overlay

- [ ] **Spell result never computed.** `InvokerOverlay.pollResult`
      (`hand_tracking/frame_overlays/invoker_overlay.py:57`) is never called, so
      `current_image` is never set. As a result:
  - [ ] `handleDisplay` (`:85`) runs every frame but never draws anything.
  - [ ] `load_images` reads every spell icon at startup for nothing.
  - [ ] The `spell_book` entry `1: ""` (`:16`) and the two `print` calls in
        `pollResult` (`:63`, `:74`) are unreachable.
  Wire `pollResult` up (for example after the third element command) or
  remove the image path.

## Gestures and settings

- [ ] **Unused distance helper.** `hand_tracking/gestures/geometry.py:25` `distance()` has
      no callers.
- [ ] **Unused classification band.** `FingerCategory.semantic_class`
      (`hand_tracking/gestures/finger_classifier.py:18`), together with the `gesture_class`
      values `VERY_CURLED` and `NEARLY_CLOSED` set for it, is never read.
- [ ] **Unused classification helper.** `SettingsData.classify_finger_deviation`
      (`hand_tracking/settings/settings_manager.py:123`) has no callers. The settings
      preview uses `FingerThresholds.classify`.
- [ ] **Unused profile action.** `GestureProfileManager.add_profile`
      (`hand_tracking/gestures/profile_manager.py:146`) has no callers. Profiles are
      created through `MappingSession.create_profile`.

## UI

- [ ] **Unused overlay setter.** `ClickThroughOverlayWindow.set_background_opacity`
      (`hand_tracking/ui/components/overlays/window.py:98`) has no callers.
      `HandTrackingOverlay` sets `background_opacity` and refreshes directly.
- [ ] **Unused alias.** `SettingsForm.path_var`
      (`hand_tracking/ui/settings_panel/settings_form.py:18`) is never read.

## Files and assets

- [ ] **Unused sound helper.** `hand_tracking/sounds/BeepPlayer.py` is not imported anywhere.
- [ ] **Unused model bundle.** `tasks/gesture_recognizer.task` is never loaded.
      Only `tasks/hand_landmarker.task` is the default model.
- [ ] **Unused UI dependency.** `requirements-ui.txt` installs `dearpygui` and
      `dearpygui-ext`, which no module imports. The UI is Tkinter.
