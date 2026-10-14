"""Theme identities shared by persistence and UI providers without importing Tk."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeChoice:
    name: str
    style_name: str
    family: str
    dark: bool = False


THEME_CHOICES = (
    ThemeChoice("Light", "sun-valley-light", "standard"),
    ThemeChoice("Dark", "sun-valley-dark", "standard", dark=True),
    ThemeChoice("Nier Light", "nier-automata-light", "nier"),
    ThemeChoice("Nier Dark", "nier-automata-dark", "nier", dark=True),
)
THEMES = tuple(choice.name for choice in THEME_CHOICES)
_CHOICES_BY_NAME = {
    name.casefold(): choice
    for choice in THEME_CHOICES
    for name in (choice.name, choice.style_name)
}


def resolve_theme(value):
    name = str(value).strip().casefold()
    choice = _CHOICES_BY_NAME.get(name)
    if choice is not None:
        return choice
    # Preserve the previous migration behavior for older saved theme names.
    return THEME_CHOICES[1 if name.endswith("dark") else 0]
