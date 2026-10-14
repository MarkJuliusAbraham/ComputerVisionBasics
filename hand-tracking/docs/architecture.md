# Current core architecture

This describes the code as it stands on 2026-10-13. Solid arrows represent data
or calls; dashed arrows represent configuration, scheduling, or feedback.

How the application starts, which component owns each resource, and how it
shuts down are described in `startup_lifecycle.md`.

## Visual key

| Appearance | Meaning |
| --- | --- |
| Blue rectangle | Processing class, method, or operation |
| Blue diamond | Condition / execution branch |
| Gold parallelogram | Data object or returned result |
| Green rounded rectangle | User interface / display |
| Purple cylinder | Saved configuration file |
| Gray hexagon | External device, library runtime, or receiving application |

Data objects can themselves be Python classes; the distinction here is their
responsibility. Processing components act on values, while data objects carry
them. The shapes and theme-derived colors match `functionality_diagrams.md`.

## Webcam to commands and displays

```mermaid
%%{init: {"theme": "base", "htmlLabels": false, "flowchart": {"htmlLabels": false}, "themeCSS": ".edgeLabel rect, .labelBkg { fill: #ffffff !important; opacity: 1 !important; }", "themeVariables": {"primaryTextColor": "#202020", "textColor": "#202020", "lineColor": "#8a8a8a", "edgeLabelBackground": "#ffffff", "clusterBkg": "#f7f7f7", "clusterBorder": "#808080", "titleColor": "#202020", "background": "#ffffff"}}}%%
flowchart TD
    Webcam{{"Webcam"}}:::external --> Capture["Camera · capture worker<br/>OpenCV VideoCapture.read"]:::component
    Capture --> Frames[/"Latest frame buffer<br/>BGR NumPy image"/]:::data
    Frames --> App["Application · Tk event-loop tick<br/>Read a frame copy; check tracking state"]:::component

    App --> Tracker["HandTracker"]:::component
    Tracker --> Session["HandLandmarkerSession<br/>BGR → RGB; timestamp; detect_async"]:::component
    Session --> Inference{{"MediaPipe Hand Landmarker<br/>Asynchronous inference"}}:::external
    Inference -->|"Result callback"| Results[/"HandLandmarkerResult<br/>Cached landmarks + handedness"/]:::data
    Results --> Poll["HandTracker.detect<br/>Return the latest completed result"]:::component
    Session --> Poll
    Poll --> Detector["Detector<br/>FingerClassifier + PalmDetector"]:::component
    Detector --> State[/"GestureState<br/>Palm, finger deviations/classes/tips, wrist"/]:::data

    State --> Handler["GestureHandler<br/>Reset rule, matching, input latch,<br/>fingertip tracking and repeats"]:::component
    Handler --> Definition[/"GestureDefinition or none<br/>Matched gesture for reporting"/]:::data
    Definition -->|"Contains"| Sequence[/"CommandSequence<br/>Steps + delays"/]:::data
    Sequence -->|"Eligible initial action or repeat"| Executor["CommandExecutor<br/>Queue key taps, releases and delays"]:::component
    Executor --> Input["InputSimulator<br/>pynput.keyboard.Controller"]:::component
    Input --> OS{{"OS keyboard events<br/>Consumed by the receiving application"}}:::external
    App -. "Advance due command actions each tick" .-> Executor

    State --> Records[/"HandReport list<br/>Hand state + matched gesture"/]:::data
    Definition --> Records
    Records --> Module["HandTrackingModule.update_data<br/>HandDebugPanel constructs the shared report"]:::component
    Module --> Report[/"LiveHandData<br/>Hand records + tracking status"/]:::data
    Report --> Debug("Hand debugging UI<br/>Left/right summaries and deviation bars"):::view
    Report --> Overlay("Optional desktop overlay<br/>RGBA renderer → Windows layered window"):::view
    Report --> SettingsPreview("Optional settings preview<br/>Live finger data + draft thresholds"):::view

    App --> Compose["Application · camera-frame composition<br/>Landmarks, mirror, paths and feedback"]:::component
    Results --> Compose
    Handler --> Paths[/"Drawing paths<br/>Selected fingertips + repeat markers"/]:::data
    Paths --> Compose
    Executor -. "Released-key callback" .-> Invoker["InvokerOverlay<br/>Command feedback"]:::component
    Invoker --> Compose
    Compose --> DisplayFrame[/"Annotated camera frame"/]:::data
    DisplayFrame --> Preview("CameraPreview · display worker<br/>Latest frame → imshow + waitKey"):::view

    classDef component fill:#d1e7f7,stroke:#0078d4,color:#202020,stroke-width:2px;
    classDef data fill:#f1ecdc,stroke:#76601f,color:#202020,stroke-width:2px;
    classDef view fill:#dfece3,stroke:#28643a,color:#202020,stroke-width:2px;
    classDef config fill:#ece6f0,stroke:#67437d,color:#202020,stroke-width:2px;
    classDef external fill:#e2e2e2,stroke:#606060,color:#202020,stroke-width:2px;
```

### Important execution details

- Arrows show where information goes; data objects do not invoke the next
  component themselves. `Application` performs the calls between stages.
- `Application` receives its collaborators in three groups: `VideoIO` (camera
  and preview window), `HandPipeline` (tracker, detector, gesture handler),
  and `FrameOverlays` (everything drawn on the frame). Each group closes its
  own resources. `TrackingSwitches` holds the enable, pause, and
  command-activity switches that decide whether a frame is analyzed.
- `Application` coordinates the frame loop through Tk's `after` callbacks.
  Gesture classification, matching, command scheduling, and UI updates run on
  that thread.
- `Camera` captures independently and publishes a latest-frame buffer and a
  `CameraStatus`. The application receives a copy because it modifies the
  displayed frame, and passes the frame's aspect ratio to the detector.
- `HandLandmarkerSession.detect` submits a new image and returns its cached
  result. The returned landmarks can belong to an earlier frame; the application
  does not wait for the newly submitted image to finish inference.
- `ModelLoader` has a separate worker for creating and retiring model sessions.
  The model callback stores results and latency measurements; it does not
  update Tk widgets or simulate input.
- `CommandExecutor.execute` calls `update` immediately. A first key press can
  occur during gesture handling if the executor is free. Releases, later steps,
  and repeats are advanced on subsequent application ticks. The current key
  hold duration is 50 ms.
- Matched gesture, palm, and tracking-status changes refresh the UI immediately
  on the processing tick. Ongoing finger data with the same report identity is
  throttled to approximately 100 ms between updates.
- The desktop overlay consumes the same `LiveHandData` as the debugger. It
  does not run another detector. The camera preview has its own OpenCV window
  thread and retains only the latest submitted frame.
- Tracking respects the model status, tracking enablement, and manual pause.
  The active debugging page or enabled desktop overlay permits commands. A
  settings preview can request detection with command invocation disabled.

## Inside the gesture handler

```mermaid
%%{init: {"theme": "base", "htmlLabels": false, "flowchart": {"htmlLabels": false}, "themeCSS": ".edgeLabel rect, .labelBkg { fill: #ffffff !important; opacity: 1 !important; }", "themeVariables": {"primaryTextColor": "#202020", "textColor": "#202020", "lineColor": "#8a8a8a", "edgeLabelBackground": "#ffffff", "clusterBkg": "#f7f7f7", "clusterBorder": "#808080", "titleColor": "#202020", "background": "#ffffff"}}}%%
flowchart TD
    State[/"GestureState"/]:::data --> Wrist["WristMovementHistory<br/>Record motion within the lookback window"]:::component
    Wrist --> Reset{"Matches profile reset rule?"}:::decision
    Reset -->|Yes| Clear["GestureHandler<br/>Clear commands, repeats and drawings;<br/>unlock input when invocation is enabled"]:::component
    Reset -->|No| Match["GestureMatcher<br/>Search valid profile definitions"]:::component
    Match --> Definition[/"GestureDefinition or none<br/>Matched result for live reporting"/]:::data
    Definition --> Mode{"Command invocation enabled?"}:::decision
    Mode -->|No| Report[/"Matched result<br/>Returned for UI / settings preview"/]:::data
    Mode -->|Yes| Locked{"Input already latched?"}:::decision
    Locked -->|Yes| Continue["GesturePathTracker / GestureHandler<br/>For the owning hand: append tips if gesture continues;<br/>otherwise finish paths and clear movement repeats"]:::component
    Continue --> Segments[/"Fingertip PathSegment mapping<br/>New movement segments, when available"/]:::data
    Segments --> Movement["MovementRepeatController<br/>Displacement gate, buffer credit,<br/>axis-weighted average path distance,<br/>distance thresholds, interval and shared limit"]:::component
    Locked -->|No| HasMatch{"Gesture matched?"}:::decision
    HasMatch -->|No| Idle[/"None<br/>No new command"/]:::data
    HasMatch -->|Yes| Start["GesturePathTracker.start<br/>MovementRepeatController.start"]:::component
    Start --> Optimistic["GestureHandler / WristMovementHistory<br/>Qualify wrist motion; reserve up to two repeats<br/>from the gesture's total repeat budget"]:::component
    Optimistic --> Request[/"CommandSequence<br/>Optional CommandModifier"/]:::data
    Request --> Execute["CommandExecutor.execute<br/>Queue the initial sequence + optional repeats"]:::component
    Execute --> Latch["GestureHandler<br/>Latch input until reset / suspension"]:::component
    Movement --> RepeatRequest[/"Gesture command sequence<br/>RepeatCrossing marker positions"/]:::data
    RepeatRequest --> RepeatExecute["CommandExecutor.execute<br/>Queue a movement repeat"]:::component
    Execute -. "When an optimistic repeat starts" .-> Markers["GesturePathTracker<br/>Mark repeat points on fingertip paths"]:::component
    RepeatExecute -. "When a movement repeat starts" .-> Markers

    classDef component fill:#d1e7f7,stroke:#0078d4,color:#202020,stroke-width:2px;
    classDef decision fill:#d1e7f7,stroke:#0078d4,color:#202020,stroke-width:2px;
    classDef data fill:#f1ecdc,stroke:#76601f,color:#202020,stroke-width:2px;
```

The matcher compares the palm rule and each configured finger's allowed
classification values. Identical conflicting criteria are excluded by
`GestureCriteriaValidator`; multiple simultaneous matches are rejected by
`GestureMatcher`. Live reporting continues even when the input latch prevents
another initial command from being issued.

## Settings and profile configuration

```mermaid
%%{init: {"theme": "base", "htmlLabels": false, "flowchart": {"htmlLabels": false}, "themeCSS": ".edgeLabel rect, .labelBkg { fill: #ffffff !important; opacity: 1 !important; }", "themeVariables": {"primaryTextColor": "#202020", "textColor": "#202020", "lineColor": "#8a8a8a", "edgeLabelBackground": "#ffffff", "clusterBkg": "#f7f7f7", "clusterBorder": "#808080", "titleColor": "#202020", "background": "#ffffff"}}}%%
flowchart LR
    SettingsUI("Hub / hand settings UI<br/>Draft → Apply"):::view --> Values[/"SettingsValues<br/>Submitted fields"/]:::data
    Values --> Apply["Application.apply_changes"]:::component
    Apply --> Settings["Settings<br/>Update and persist values"]:::component
    Settings --> SettingsData[/"SettingsData<br/>Applied configuration"/]:::data
    Settings --> SettingsFile[("Settings JSON")]:::config
    SettingsData -. "Thresholds, calculation, segment count" .-> Detector["Detector"]:::component
    SettingsData -. "Optimistic tracking options" .-> Wrist["WristMovementHistory"]:::component
    SettingsData -. "Selected model path" .-> Loader["HandLandmarkerAsset + ModelLoader<br/>Validate and load model asynchronously"]:::component
    SettingsData -. "Theme / scale" .-> Theme["Theme provider<br/>apply_theme"]:::component
    Theme --> Display("Windows and panel display"):::view

    MappingUI("Mapping UI<br/>Draft → Save / select profile"):::view --> Session["MappingSession + GestureProfileManager"]:::component
    Session --> Profile[/"GestureConfig<br/>Definitions, reset rule and repeat defaults"/]:::data
    Profile -->|"Save"| ProfileFile[("Gesture profile JSON")]:::config
    Session --> SelectionFile[("Active-profile selection JSON")]:::config
    Profile --> ConfigApply["Application.apply_gesture_config"]:::component
    ConfigApply --> Handler["GestureHandler.configure<br/>Criteria, commands, tracked fingers,<br/>reset rule and repeat settings"]:::component

    OverlayUI("Overlay options<br/>Preview → Save / Discard"):::view --> OverlayData[/"OverlaySettings<br/>Style, background opacity and position"/]:::data
    OverlayData -. "Live preview" .-> Overlay["HandTrackingOverlay"]:::component
    Overlay --> OverlayView("Desktop overlay display"):::view
    OverlayData -->|"Save preferences"| Settings

    classDef component fill:#d1e7f7,stroke:#0078d4,color:#202020,stroke-width:2px;
    classDef data fill:#f1ecdc,stroke:#76601f,color:#202020,stroke-width:2px;
    classDef view fill:#dfece3,stroke:#28643a,color:#202020,stroke-width:2px;
    classDef config fill:#ece6f0,stroke:#67437d,color:#202020,stroke-width:2px;
    classDef external fill:#e2e2e2,stroke:#606060,color:#202020,stroke-width:2px;
```

Mapping drafts and settings drafts have separate commit operations. The
settings deviation preview evaluates draft thresholds without committing them
to the runtime detector. Saved mappings, selected profiles, and saved gesture
management changes notify the application through the mapping callback.

## Project layout

All Python code lives in the `hand_tracking/` package, except `main.py`, the
entry point. The folders inside it are namespace packages, so they have no
`__init__.py`; import each class from the module that defines it.

| Folder | Contents |
| --- | --- |
| `main.py` | Entry point and composition root |
| `hand_tracking/app/` | Application coordination: the frame loop, its collaborators, and frame timing |
| `hand_tracking/capture/` | Camera capture on a worker thread, its published status, and the preview window |
| `hand_tracking/landmarker/` | Model assets, loading, and inference for the hand landmark backend |
| `hand_tracking/gestures/` | Finger classification, gesture matching, profiles, and movement rules (`optimistic/`, `tracking/`, `repeating/`) |
| `hand_tracking/input/` | Command scheduling and keyboard simulation |
| `hand_tracking/frame_overlays/` | Drawings added to the camera frame, including the Invoker overlay and its images |
| `hand_tracking/settings/` | Settings data, validation, and persistence code |
| `hand_tracking/common/` | Dependency-free helpers and the project folder locations (`project_paths.py`) |
| `hand_tracking/ui/` | Tkinter control surface: `core/` window composition and shared state, `components/` reusable widgets, and the feature panels |
| `hand_tracking/sounds/` | Unused sound helper (see `dead_code_checklist.md`) |
| `settings/` | Saved settings and the active gesture profile selection (JSON) |
| `gesture_profiles/` | Saved gesture profiles |
| `tasks/` | MediaPipe model bundles |
| `docs/`, `tests/` | Documentation and behavior tests |

## Main code locations

| Responsibility | Location |
| --- | --- |
| Startup and dependency composition | `main.py` builds `VideoIO`, `HandPipeline`, and `FrameOverlays` (`hand_tracking/app/components.py`) |
| Frame processing and coordination | `hand_tracking/app/application.py`, `hand_tracking/app/frame_profiler.py` |
| Camera capture and device switching | `hand_tracking/capture/camera.py`, `hand_tracking/capture/camera_status.py` |
| Tracker facade and inference session | `hand_tracking/landmarker/hand_tracker.py`, `hand_tracking/landmarker/session.py` |
| Asynchronous model loading | `hand_tracking/landmarker/model_loader.py` |
| Hand landmark model (indices, fingers, handedness) | `hand_tracking/gestures/hand_landmarks.py` |
| Landmark classification | `hand_tracking/gestures/detector.py`, `hand_tracking/gestures/finger_classifier.py`, `hand_tracking/gestures/finger_thresholds.py`, `hand_tracking/gestures/palm_detector.py` |
| Gesture orchestration and matching | `hand_tracking/gestures/gesture_handler.py`, `hand_tracking/gestures/gesture_matcher.py` |
| Wrist history, paths and movement repeats | `hand_tracking/gestures/optimistic/`, `hand_tracking/gestures/tracking/`, `hand_tracking/gestures/repeating/` |
| Command scheduling and keyboard simulation | `hand_tracking/input/command_executor.py`, `hand_tracking/input/input_simulator.py` |
| Shared hand UI report and views | `hand_tracking/ui/tracking/hand/module.py`, `hand_tracking/ui/tracking/hand/debug_panel/` |
| Desktop overlay | `hand_tracking/ui/tracking/hand/overlay/`, `hand_tracking/ui/components/overlays/` |
| Camera-frame drawings and preview window | `hand_tracking/frame_overlays/`, `hand_tracking/capture/camera_preview.py` |
| Settings and gesture-profile persistence | `hand_tracking/settings/settings_manager.py`, `hand_tracking/gestures/gesture_config.py`, `hand_tracking/gestures/profile_manager.py`, `hand_tracking/common/json_storage.py`, `hand_tracking/common/config_values.py` |
