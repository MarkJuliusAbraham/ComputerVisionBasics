# Core behavior tests

Runtime reliability tests:

- `test_application_lifecycle.py`: fatal frame/profiler errors, UI heartbeat,
  immediate overlay hiding, command cancellation, and cleanup ordering.
- `test_model_loader.py`: concurrent session leases and bounded shutdown with
  blocked native loading, submission, or closure.
- `test_overlay_cleanup.py`: injected teardown failures and partial GUI startup.
- `test_diagnostics.py`: persistent logs, thread dumps, restored exception hooks,
  and diagnostic shutdown even when its watchdog is stuck.

`test_settling_gate.py` checks motion-aware candidate replacement, inference
timestamp caching, relevant fingers, wrist independence, resets, bypass,
settings validation and actual command gating with a mocked input executor.

`test_finger_hysteresis.py` checks directional boundaries, per-hand/per-finger
memory, skipped bands, zero-margin bypass, loss/reset behavior, preserved
measurements, and settings validation/serialization.

`test_landmark_filter.py` checks optional One Euro coordinate filtering,
exact bypass, timestamp caching, input preservation, adaptive speed response,
tracking-loss resets, and settings validation/serialization.

`test_distance_repeats.py` checks the Distance trigger: every X average selected
fingertip path distance earns one repeat, including reverse movement, with leftover
distance carried forward. It bypasses starting buffers and optimistic repeats,
remembers the triggered gesture until reset, and retains the repeat limit and delay.

Run the tests from the `hand-tracking` directory using the project's environment:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

`test_core_contracts.py` checks lasting contracts:

1. Saved settings survive an application reload.
2. Saved profiles preserve gestures, their criteria, tracking choices, and commands.
3. An invalid profile cannot replace an existing valid profile.
4. Cancelling commands releases held input and prevents pending commands and repeats.
5. Backend code never imports frontend code.

`test_optimistic_tracking.py` checks wrist-motion qualification with synthetic paths and a fake clock:
resting jitter after a small move does not qualify, deliberate movement does, cached detections count once,
hand-size scaling treats the same motion alike near and far, and older settings files still load.

`test_pose_capture.py` checks that a captured pose matches itself, the most frequent band wins over brief
flicker, straight or closed fingers gain the allowance toward the middle while middle bands stay exact, an inconsistent palm stays unrestricted, and only the first hand seen is captured.

Each test uses synthetic data and temporary files. Input is injected as a recorder, and time is controlled without sleeping. No GUI, camera, model, or real keyboard controller is created. The application dependencies must still be installed to import its modules.

`test_shake_repeats.py` checks required travel plus return near the motion origin,
jitter and drift rejection, timing, palm-size scaling, missing samples, repeat limits and cancellation,
the existing distance trigger, and repeat-setting/draft serialization. The Repeat
Commands section offers Tracking or Shake per gesture (or Apply to all gestures).
Shake remembers the last triggered gesture despite finger-pose changes, uses wrist
motion averaged across the wrist and all fingertips, independently of selected
tracking fingers, and bypasses optimistic repeats. An explicit
reset clears the remembered gesture; pause and hand loss discard partial shakes
and pending repeats while retaining the gesture and its remaining repeat budget.

These tests assert public behavior rather than widget layout, private fields, shipped profile contents, or performance timings. Changes to those details should not require test changes. A deliberate public API or behavior change can still require an update.

