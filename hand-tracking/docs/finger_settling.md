# Finger settling gate

In hand tracking settings, find **Finger settling**, enable **Wait for fingers
to settle before activation**, and Apply. It defaults to off. The initial
maximum bend speed is 90 degrees/second; this is a tuning starting point.

The gate estimates absolute changes in each finger's deviation angle divided
by the interval between inference timestamps. It watches the matched gesture's
constrained fingers and any single finger currently preventing another gesture
with compatible palm criteria from matching. Other finger movement and wrist
translation do not block activation. Palm-only mappings with no relevant finger
constraints bypass the finger check.

A matched gesture is a candidate until every relevant speed is at or below
the limit. The latest matching gesture replaces the previous candidate. Nothing
is queued for a candidate that stops matching. Normal live gesture labels still
show matches before commands activate. Only initial activation is gated; reset
commands, command latching, and active repeats retain their existing behavior.

There is no fixed dwell timer. A newly seen hand requires two fresh inference
results to estimate speed. Cached results reuse the previous speed estimate;
they cannot make a moving candidate settle. Missing hands, suspension, profile
changes, and gaps longer than 250 ms discard motion history. Preview-only calls
do not accumulate activation history. Hand identity follows the existing
handedness-based gesture pipeline.

Lower limits reject more transitional movement, but jitter may postpone
activation. Higher limits permit faster activation but can admit intermediate
poses. Zero requires exactly unchanged angles. Unchecking the gate bypasses it.
One Euro filtering affects the angles supplied to the gate and therefore its
tuning. Finger hysteresis changes categories, while the gate uses continuous
deviation angles.

This is a motion heuristic, not an intent predictor: a slowly traversed or
briefly stationary intermediate pose may still activate. Validate it with your
actual gestures before relying on it to replace a previous buffer.
