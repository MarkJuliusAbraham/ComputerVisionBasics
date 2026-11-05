# Hand tracking

Webcam hand tracking with MediaPipe: finger classification, gesture matching,
and keyboard commands, with a Tkinter control window.

## Setup

From this folder, with Python 3.11 or newer:

```bash
python -m venv .venv
```

Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

macOS:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

## macOS notes

- **Tkinter.** Python from python.org includes it. With Homebrew Python, run
  `brew install python-tk` first.
- **Permissions.** In System Settings → Privacy & Security, allow the app you
  launch from (Terminal, iTerm or your editor):
  - **Camera**, for the webcam. macOS asks on first use.
  - **Accessibility** and **Input Monitoring**, so gestures can send keys.
    Without them, pynput's key presses are silently ignored.

  Restart that app after granting a permission.
- **Camera choice.** The app starts on camera index 0 on macOS (index 1 on
  Windows). If that is the wrong camera, pick another in the hub's camera list.
- **Camera preview.** On macOS the preview is drawn in a Tk window, refreshed
  up to 30 times a second. Windows uses OpenCV's own window.
- **Desktop overlay.** The click-through overlay uses Windows-only APIs. On
  macOS, turning it on shows an error and the rest of the app keeps working.
- **Saved paths.** Settings and the profile selection store paths inside this
  folder relative to it, so they work on both systems. An absolute path saved
  on the other system falls back to the bundled model and profiles.

## Platform differences

Everything the app does differently per operating system lives in
`hand_tracking/frontend/platforms/`. `main.py` picks a `Platform` once
(`current_platform()`) and passes it to the parts that need it: the camera
preview, title-bar coloring, the desktop overlay and its fonts, DPI setup, and
the default camera. Components never check `sys.platform` themselves; a test
enforces this.

## Tests

```bash
python -B -m unittest discover -s tests -v
```

See `tests/README.md` and `docs/` for details.
