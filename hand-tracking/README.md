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

- **Python and Tk version (important).** Use **Python 3.13 or newer from
  python.org** on macOS. Its installer bundles Tk 8.6.15 or later. Tk is part
  of the Python install, not a pip package, so `pip` cannot update it.
  Tk **8.6.12 and older** has a known macOS bug where clicks are ignored,
  especially when switching tabs ([python/cpython#110218](https://github.com/python/cpython/issues/110218));
  it was fixed in Tk 8.6.13. Check the version with:

  ```bash
  .venv/bin/python -c "import tkinter, sys; print(sys.version); print(tkinter.Tcl().eval('info patchlevel'))"
  ```

  If it prints 8.6.12 or lower, install a newer Python and recreate `.venv`
  from it (`python3.13 -m venv .venv`, then install `requirements.txt`).
  MediaPipe's macOS package works with any Python 3 version on Apple Silicon.
  With Homebrew Python instead, install `python-tk` for the same version
  (for example `brew install python-tk@3.13`).
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
- **Desktop overlay.** Keyboard commands only run while you can see the
  tracker: the hand-tracking window's Main tab, or the desktop overlay. The
  overlay is click-through, has a transparent background, and stays on top,
  including over apps in full-screen mode. On the Main tab, **Overlay shows**
  switches it between **Stats** (the hand panels) and **Camera and stats**
  (the camera picture above them, in a Small, Medium or Large width; the
  preview window steps aside while it shows). With the overlay on, you can
  minimize every other window and commands keep running.

  On macOS the overlay is a native AppKit panel and needs `pyobjc`
  (installed by `requirements.txt`). To move it, open **Overlay settings…**,
  click **Reposition overlay**, drag it, then click **Done positioning**.
- **App Nap.** macOS slows apps you are not looking at. `requirements.txt`
  installs `pyobjc` on macOS so the app can opt out while it runs; without it
  a warning is logged and tracking may slow in the background.
- **UI scale.** Each operating system keeps its own UI scale in
  `settings/settings.json` (`ui_scales`), so a scale chosen on Windows does not
  enlarge the macOS windows. macOS starts on Auto.
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
