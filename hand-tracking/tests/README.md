# Core behavior tests

Run these five tests from the `hand-tracking` directory using the project's environment:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

They check lasting contracts:

1. Saved settings survive an application reload.
2. Saved profiles preserve gestures, their criteria, tracking choices, and commands.
3. An invalid profile cannot replace an existing valid profile.
4. Cancelling commands releases held input and prevents pending commands and repeats.
5. Backend code never imports frontend code.

Each test uses synthetic data and temporary files. Input is injected as a recorder, and time is controlled without sleeping. No GUI, camera, model, or real keyboard controller is created. The application dependencies must still be installed to import its modules.

These tests assert public behavior rather than widget layout, private fields, shipped profile contents, or performance timings. Changes to those details should not require test changes. A deliberate public API or behavior change can still require an update.

