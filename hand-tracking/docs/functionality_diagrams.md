# Core functionality: three audience views

The diagrams distinguish the things that do work from the information they
exchange. Data objects can themselves be Python classes; their role here is to
carry values.

## Visual key

| Appearance | Meaning |
| --- | --- |
| Blue rectangle | Processing component; named classes in the developer view |
| Gold parallelogram | Data passed between components |
| Green rounded rectangle | User interface / display |
| Purple cylinder | Saved settings or profile files |
| Gray hexagon | External device, library runtime, or receiving application |

Solid arrows show information or results passing between nodes. Dashed arrows
show configuration or control calls. Diagram colors are derived from the
application's Light theme palette, with pale fills for readable labels.

## 1. General audience: what happens to your movement

**Audience:** Someone seeing the project for the first time.

```mermaid
flowchart LR
    Webcam{{"Webcam"}}:::external --> Video[/"Live video"/]:::data
    Video --> Understand["Read your hand<br/>and recognize a gesture"]:::component
    Understand --> Result[/"Hand position<br/>and recognized gesture"/]:::data
    Result -->|"Gesture matched"| Send["Send the assigned<br/>keyboard command"]:::component
    Send --> OtherApp{{"Your application"}}:::external
    Result --> Feedback("Live feedback<br/>on screen"):::view

    classDef component fill:#d1e7f7,stroke:#0078d4,color:#202020,stroke-width:2px;
    classDef data fill:#f1ecdc,stroke:#76601f,color:#202020,stroke-width:2px;
    classDef view fill:#dfece3,stroke:#28643a,color:#202020,stroke-width:2px;
    classDef external fill:#e2e2e2,stroke:#606060,color:#202020,stroke-width:2px;
```

The blue blocks do work, the gold blocks show what they learn, and the green
block shows that information to the user.

## 2. Project collaborators: processing versus information

**Audience:** A designer, collaborator, or someone interested in how the
features connect.

```mermaid
flowchart TD
    Webcam{{"Webcam"}}:::external --> Locate["Locate hand joints"]:::component
    Locate --> Landmarks[/"Finger and wrist<br/>positions"/]:::data
    Landmarks --> Classify["Evaluate finger bend<br/>and palm direction"]:::component
    Classify --> HandState[/"Hand pose<br/>and finger classifications"/]:::data
    HandState --> Recognize["Recognize gestures<br/>and apply movement / repeat rules"]:::component
    Landmarks --> Recognize
    Recognize --> Selection[/"Matched gesture<br/>and its commands"/]:::data
    Selection --> Execute["Schedule and send<br/>keyboard actions"]:::component
    Execute --> OtherApp{{"Receiving application"}}:::external

    HandState --> Dashboard("Hand and gesture display<br/>Optional desktop overlay"):::view
    Selection --> Dashboard
    Recognize --> Drawing[/"Movement paths<br/>and repeat markers"/]:::data
    Drawing --> Preview("Annotated camera preview"):::view
    Webcam -->|"Video"| Preview

    Settings[("Saved settings")]:::config -.-> Classify
    Settings -.-> Recognize
    Profiles[("Gesture profiles")]:::config -.-> Recognize

    classDef component fill:#d1e7f7,stroke:#0078d4,color:#202020,stroke-width:2px;
    classDef data fill:#f1ecdc,stroke:#76601f,color:#202020,stroke-width:2px;
    classDef view fill:#dfece3,stroke:#28643a,color:#202020,stroke-width:2px;
    classDef config fill:#ece6f0,stroke:#67437d,color:#202020,stroke-width:2px;
    classDef external fill:#e2e2e2,stroke:#606060,color:#202020,stroke-width:2px;
```

The processing blocks combine several implementation classes. The recognition
block includes gesture matching, wrist history, selected-fingertip tracking,
reset behavior, and repeat rules. Tracking state and the input latch determine
whether a matched gesture can send a new command.

## 3. Developers: classes, data objects, and views

**Audience:** Someone maintaining the code or tracing its data flow.

```mermaid
flowchart TD
    Webcam{{"Webcam"}}:::external --> Camera["Camera<br/>Capture worker"]:::component
    Camera --> Frame[/"Frame<br/>BGR NumPy image"/]:::data
    Frame --> App["Application<br/>Tk event-loop coordinator"]:::component
    App --> Tracker["HandTracker"]:::component
    Tracker --> Session["HandLandmarkerSession"]:::component
    Session -->|"Image + timestamp"| MP{{"MediaPipe<br/>Hand Landmarker"}}:::external
    MP -->|"Async callback"| Result[/"HandLandmarkerResult<br/>Landmarks + handedness<br/>Cached in the session"/]:::data
    Result -->|"Latest available landmarks"| Detector["Detector<br/>FingerClassifier + PalmDetector"]:::component
    Detector --> State[/"GestureState<br/>Palm, fingers and wrist"/]:::data

    State --> Handler["GestureHandler<br/>Match / reset / latch<br/>Tracking and repeats"]:::component
    Handler --> Definition[/"GestureDefinition or none<br/>Currently matched gesture"/]:::data
    Definition -->|"Contains"| Sequence[/"CommandSequence<br/>Steps + delays"/]:::data
    Sequence -->|"Eligible initial action or repeat"| Executor["CommandExecutor"]:::component
    Executor --> Simulator["InputSimulator"]:::component
    Simulator --> OS{{"OS keyboard input<br/>pynput"}}:::external
    App -. "Advance scheduled actions" .-> Executor

    State --> Module["HandTrackingModule"]:::component
    Definition --> Module
    Module --> Report[/"LiveHandData<br/>Per-hand state + gesture<br/>Tracking status"/]:::data
    Report --> Debug("Hand debugging views"):::view
    Report --> Overlay("HandTrackingOverlay<br/>RGBA desktop presentation"):::view
    Report --> SettingsPreview("Deviation settings preview"):::view

    App --> DisplayFrame[/"Annotated frame<br/>Landmarks, paths,<br/>repeat markers and feedback"/]:::data
    DisplayFrame --> Video("CameraPreview<br/>OpenCV display worker"):::view
    Handler --> Paths[/"Drawing paths<br/>and repeat markers"/]:::data
    Paths -->|"Used during composition"| DisplayFrame

    ConfigFiles[("Settings and profile JSON")]:::config --> SettingsData[/"SettingsData"/]:::data
    ConfigFiles --> GestureConfig[/"GestureConfig"/]:::data
    SettingsData -.-> Detector
    SettingsData -. "Optimistic tracking" .-> Handler
    GestureConfig -.-> Handler

    classDef component fill:#d1e7f7,stroke:#0078d4,color:#202020,stroke-width:2px;
    classDef data fill:#f1ecdc,stroke:#76601f,color:#202020,stroke-width:2px;
    classDef view fill:#dfece3,stroke:#28643a,color:#202020,stroke-width:2px;
    classDef config fill:#ece6f0,stroke:#67437d,color:#202020,stroke-width:2px;
    classDef external fill:#e2e2e2,stroke:#606060,color:#202020,stroke-width:2px;
```

### Reading the developer view

- `Application` performs the calls between pipeline stages. The arrows show
  where information goes; data objects do not call the next component themselves.
- `HandTracker.detect` delegates to the active `HandLandmarkerSession`, which
  submits an image and returns the latest completed result. The callback and
  the application's result consumption occur independently; the application
  does not wait for that submission to finish.
- `GestureDefinition` is the match returned for reporting. Command invocation
  also depends on tracking activity, reset/latch state, and repeat eligibility.
  The path through `CommandSequence` illustrates an eligible command request.
- `HandTrackingModule` passes hand reports into `HandDebugPanel`, where
  `LiveHandData` is constructed. That same report feeds the debugger, desktop
  overlay, and settings preview.
- `GestureHandler` uses `GestureMatcher`, `WristMovementHistory`,
  `GesturePathTracker`, and `MovementRepeatController`. These helpers are
  grouped within the handler block in this view.
- `HandDrawer`, `GesturePathOverlay`, and `InvokerOverlay` contribute to the
  annotated frame under `Application`'s coordination. `CameraPreview` receives
  the finished image, not the raw path objects.
- Capture, inference, model loading, and the camera preview run outside the Tk
  thread. Classification, gesture handling, command scheduling, and ordinary
  Tk UI updates run on its event loop.
- The settings preview can use draft thresholds with command invocation
  disabled. Ongoing finger reports with unchanged gesture/status identity are
  refreshed approximately every 100 ms.

See `architecture.md` for additional handler and configuration detail.
