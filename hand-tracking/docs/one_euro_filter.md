# One Euro landmark filtering

Open the hand tracking settings and find **One Euro Filter**. Check
**Filter landmark coordinates**, then Apply. Uncheck and Apply to compare
with raw MediaPipe coordinates. Existing settings files default to off.

- **Minimum cutoff (Hz)** starts at 1.0. Lower values smooth resting jitter
  more strongly but increase lag.
- **Speed response (beta)** starts at 0.5. Higher values follow fast movement
  more closely, with less smoothing during motion.

The optional layer filters x, y, and z of image-space landmarks before
both drawing and gesture analysis. World landmarks are preserved unchanged.
It uses inference timestamps, processes each result once, and reuses the
filtered result between callbacks. It does not modify MediaPipe's raw result.
Filters reset when settings or model sessions change, a hand disappears,
or the interval between results exceeds 250 ms. Channels are separated by
handedness; this is not an identity tracker for crossing hands.

Optimistic Tracking's wrist smoothing is separate and can compound this
smoothing. The cutoff and beta defaults are starting points, not calibrated
values or a guarantee of reduced latency.

Algorithm: Casiez, Roussel and Vogel,
[1€ Filter (CHI 2012)](https://gery.casiez.net/publications/CHI2012-casiez.pdf).
