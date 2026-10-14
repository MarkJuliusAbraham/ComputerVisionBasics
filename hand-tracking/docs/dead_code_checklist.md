# Dead code checklist

Code that is never called, or whose result is never used. All of it is still
in the codebase. Tick an item once it has been removed, wired up, or kept on
purpose.

Line numbers are from the October 2026 refactor and may drift.

## Startup and application loop

- [ ] **Unused image overlay.** `create_frame_overlays` (`main.py:46`) builds
      `ImageOverlay()`, which reads `image_module/images/absolute_cinema.jpg`
      from disk and prints a message at every startup. It is stored as
      `FrameOverlays.image` (`app_components.py:96`) and never drawn.
      Files: `image_module/image_overlay.py`, `main.py`, `app_components.py`.
- [ ] **Restart loop that never repeats.** `Application.restart_requested`
      (`application.py:70`) is set to `False` and never changes, so the
      `while True` loop in `main.py:64` always runs exactly once. The Restart
      button calls `request_restart`, which resets the pipeline in place.
      `settings.load()` at the top of that loop repeats the load already done by
      `Settings()`.
- [ ] **Unused import.** `import os` in `main.py:1`.
- [ ] **Unread theme name.** `Application.theme` (`application.py:64`, set at
      `:113`) is written on every settings change and never read. The control
      window applies the theme from `SettingsData` directly.
- [ ] **No-op frame profiler stages.** `FrameProfiler.measure`
      (`frame_profiler.py:27`) yields without measuring. It wraps 13 blocks in
      the frame loop in `application.py`. Either measure the stages or remove the
      wrappers.

## Camera

- [ ] **Unused properties.** `Camera.switching` (`camera.py:28`) and
      `Camera.cap` (`camera.py:37`) have no callers. The UI reads
      `CameraStatus.is_switching` instead.
- [ ] **Unread aspect ratio.** `Camera.aspect` (`camera.py:11`, updated at
      `camera.py:91`) used to be read by `gestures/geometry.py` as a hidden
      global. Detection now receives the analyzed frame's aspect ratio from
      `HandPipeline.analyze`, so nothing reads this value.

## Invoker overlay

- [ ] **Spell result never computed.** `InvokerOverlay.pollResult`
      (`custom_overlay/invoker_overlay.py:57`) is never called, so
      `current_image` is never set. As a result:
  - [ ] `handleDisplay` (`:85`) runs every frame but never draws anything.
  - [ ] `load_images` reads every spell icon at startup for nothing.
  - [ ] The `spell_book` entry `1: ""` (`:16`) and the two `print` calls in
        `pollResult` (`:63`, `:74`) are unreachable.
  Wire `pollResult` up (for example after the third element command) or
  remove the image path.

## Gestures and settings

- [ ] **Unused distance helper.** `gestures/geometry.py:25` `distance()` has
      no callers.
- [ ] **Unused classification band.** `FingerCategory.semantic_class`
      (`gestures/finger_classifier.py:18`), together with the `gesture_class`
      values `VERY_CURLED` and `NEARLY_CLOSED` set for it, is never read.
- [ ] **Unused classification helper.** `SettingsData.classify_finger_deviation`
      (`settings/settings_manager.py:124`) has no callers. The settings
      preview uses `FingerThresholds.classify`.
- [ ] **Unused profile action.** `GestureProfileManager.add_profile`
      (`gestures/profile_manager.py:149`) has no callers. Profiles are
      created through `MappingSession.create_profile`.

## UI

- [ ] **Unused overlay setter.** `ClickThroughOverlayWindow.set_background_opacity`
      (`gui_tkinter/components/overlays/window.py:98`) has no callers.
      `HandTrackingOverlay` sets `background_opacity` and refreshes directly.
- [ ] **Unused alias.** `SettingsForm.path_var`
      (`gui_tkinter/settings_panel/settings_form.py:18`) is never read.

## Files and assets

- [ ] **Unused sound helper.** `sounds/BeepPlayer.py` is not imported anywhere.
- [ ] **Unused model bundle.** `tasks/gesture_recognizer.task` is never loaded.
      Only `tasks/hand_landmarker.task` is the default model.
- [ ] **Unused UI dependency.** `requirements-ui.txt` installs `dearpygui` and
      `dearpygui-ext`, which no module imports. The UI is Tkinter.
