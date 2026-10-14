import math


def vector(a, b, aspect=1.0):
    """Landmark difference with x/z scaled by the frame's width/height ratio.

    MediaPipe normalizes x by width and y by height; the aspect ratio makes
    the axes comparable. Callers pass the ratio of the frame being analyzed.
    """
    return (
        (b.x - a.x) * aspect,
        (b.y - a.y),
        (b.z - a.z) * aspect,
    )


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[0],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def distance(a, b, *, include_z=True) -> float:
    dz = a.z - b.z if include_z else 0.0

    return math.sqrt(
        (a.x - b.x) ** 2
        + (a.y - b.y) ** 2
        + dz**2
    )


def angle(a, b, c, aspect=1.0) -> float:
    ba = vector(b, a, aspect)
    bc = vector(b, c, aspect)

    magnitude_ba = math.dist((0, 0, 0), ba)
    magnitude_bc = math.dist((0, 0, 0), bc)

    if magnitude_ba < 1e-8 or magnitude_bc < 1e-8:
        return 0.0

    dot = sum(x * y for x, y in zip(ba, bc))
    cosine = max(
        -1.0,
        min(1.0, dot / (magnitude_ba * magnitude_bc)),
    )

    return math.degrees(math.acos(cosine))
