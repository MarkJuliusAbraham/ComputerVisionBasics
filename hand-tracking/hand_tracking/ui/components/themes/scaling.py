"""One rule for converting 100%-scale pixel sizes to the active UI scale."""


def scale_pixels(value, scale, minimum=None):
    """Round ``value * scale``; ``minimum`` keeps hairlines and borders visible."""
    pixels = round(value * scale)
    return pixels if minimum is None else max(minimum, pixels)
