# Finger classification hysteresis

In hand tracking settings, enable **finger classification hysteresis**, choose
a **Hysteresis margin (degrees)**, and Apply. It defaults to off with a 3-degree
margin. Zero margin also bypasses it.

Each hand and finger remembers its category independently. With a split at
45 degrees and a margin of 3, bending must exceed 48 degrees to enter the next
category; straightening must fall below 42 degrees to return. Exact boundary
values retain the current category. A newly seen finger uses the normal split
points for its initial classification. Large movements can cross multiple bands
in one update, with no confirmation timer.

Only the category changes: measured deviation and fingertip coordinates are
preserved. Runtime reports and gesture matching receive the stabilized category.
The settings panel's **Test deviation** preview still shows the directly edited
threshold bands, without hysteresis history.

State clears on hand loss, inactive tracking, camera unavailability, settings
application, and model restart/status changes. Hands are keyed by handedness,
consistent with the existing gesture pipeline, rather than persistent identity.

This layer is independent of gesture definitions and One Euro coordinate
filtering. Larger margins resist category flicker but require more movement
to change category. Choose margins small enough that your intended categories
remain reachable, especially with closely spaced split points.
