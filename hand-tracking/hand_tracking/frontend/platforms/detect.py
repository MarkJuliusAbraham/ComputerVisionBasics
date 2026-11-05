"""Pick the Platform for the running operating system: the one sys.platform check."""

import sys

from .base import MacPlatform, Platform


def current_platform(system: str = sys.platform) -> Platform:
    if system == "win32":
        # Imported only here, so other systems never load Windows bindings.
        from .windows import WindowsPlatform

        return WindowsPlatform()
    if system == "darwin":
        return MacPlatform()
    return Platform()
