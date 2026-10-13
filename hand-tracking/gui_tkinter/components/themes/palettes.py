"""Shared surface and semantic colors for every application theme.

NieR deviation colors adapt the muted plug-in chip colors shown here:
https://www.platinumgames.com/official-blog/article/9624
https://www.platinumgames.com/official-blog/wp-content/uploads/sites/2/2017/08/color_plugin.png
https://interfaceingame.com/screenshots/nierautomata-skills-chips/
Dusty rose extends the reference palette for the additional bend categories.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ButtonEdges:
    highlight: str
    shadow: str
    outline: str


@dataclass(frozen=True)
class PopupPalette:
    surface: str
    border: str


@dataclass(frozen=True)
class ActionPalette:
    background: str
    foreground: str
    hover: str
    pressed: str
    edges: ButtonEdges


@dataclass(frozen=True)
class ClassificationColor:
    fill: str
    text: str


@dataclass(frozen=True)
class ClassificationPalette:
    straight: ClassificationColor
    partial: ClassificationColor
    curled: ClassificationColor
    very_curled: ClassificationColor
    nearly_closed: ClassificationColor
    closed: ClassificationColor

    def color(self, category):
        key = getattr(category, "value", category)
        if isinstance(key, str) and key in self.__dataclass_fields__:
            return getattr(self, key)
        return self.straight


@dataclass(frozen=True)
class ThemePalette:
    surface: str
    panel: str
    field: str
    hover: str
    border: str
    foreground: str
    muted: str
    disabled: str
    selection: str
    selection_text: str
    track: str
    alert: str
    alert_surface: str
    deviation: ClassificationPalette
    destructive: ActionPalette
    button_edges: ButtonEdges
    popup: PopupPalette


PALETTES = {
    "Light": ThemePalette(
        surface="#fafafa", panel="#ffffff", field="#ffffff", hover="#e9e9e9",
        border="#c4c4c4", foreground="#202020", muted="#606060", disabled="#838383",
        selection="#0078d4", selection_text="#ffffff", track="#e1e6eb",
        alert="#b42318", alert_surface="#fee4e2",
        deviation=ClassificationPalette(
            straight=ClassificationColor("#4c9363", "#28643a"),
            partial=ClassificationColor("#b3933f", "#76601f"),
            curled=ClassificationColor("#c08148", "#8b4e23"),
            very_curled=ClassificationColor("#9875ad", "#67437d"),
            nearly_closed=ClassificationColor("#b87596", "#86465f"),
            closed=ClassificationColor("#bd6258", "#8a3931"),
        ),
        destructive=ActionPalette(
            background="#b42318", foreground="#ffffff", hover="#9a1f15", pressed="#7f1a12",
            edges=ButtonEdges("#cf5e54", "#72190f", "#7f1d15"),
        ),
        button_edges=ButtonEdges("#ffffff", "#a6a6a6", "#a6a6a6"),
        popup=PopupPalette("#ededed", "#969696"),
    ),
    "Dark": ThemePalette(
        surface="#1c1c1c", panel="#2b2b2b", field="#323232", hover="#3d3d3d",
        border="#555555", foreground="#f4f4f4", muted="#b0b0b0", disabled="#787878",
        selection="#4cc2ff", selection_text="#202020", track="#343a43",
        alert="#ff9b94", alert_surface="#532422",
        deviation=ClassificationPalette(
            straight=ClassificationColor("#8ec49e", "#8ec49e"),
            partial=ClassificationColor("#d9c17c", "#d9c17c"),
            curled=ClassificationColor("#d6aa7d", "#d6aa7d"),
            very_curled=ClassificationColor("#b8a1d0", "#b8a1d0"),
            nearly_closed=ClassificationColor("#cda0bd", "#cda0bd"),
            closed=ClassificationColor("#d9958b", "#d9958b"),
        ),
        destructive=ActionPalette(
            background="#cf857e", foreground="#211a19", hover="#dfa199", pressed="#b5716b",
            edges=ButtonEdges("#e7a39c", "#97504a", "#a96963"),
        ),
        button_edges=ButtonEdges("#626262", "#141414", "#626262"),
        popup=PopupPalette("#303030", "#777777"),
    ),
    "Nier Light": ThemePalette(
        surface="#dad7c6", panel="#e2dfce", field="#eeebdd", hover="#cbc8b7",
        border="#a5a291", foreground="#45443b", muted="#6a685d", disabled="#858274",
        selection="#45443b", selection_text="#f2efdf", track="#eeebdd",
        alert="#8f3f2c", alert_surface="#efdbcc",
        deviation=ClassificationPalette(
            straight=ClassificationColor("#899277", "#495541"),
            partial=ClassificationColor("#b6a562", "#706024"),
            curled=ClassificationColor("#a88f6e", "#745837"),
            very_curled=ClassificationColor("#929287", "#55564c"),
            nearly_closed=ClassificationColor("#b59098", "#78525c"),
            closed=ClassificationColor("#b98268", "#7f4933"),
        ),
        destructive=ActionPalette(
            background="#9d5944", foreground="#f2efdf", hover="#8c4e3d", pressed="#7b4234",
            edges=ButtonEdges("#ba7860", "#693b2d", "#704031"),
        ),
        button_edges=ButtonEdges("#f4f1e2", "#999583", "#999583"),
        popup=PopupPalette("#cbc7b4", "#878372"),
    ),
    "Nier Dark": ThemePalette(
        surface="#25251f", panel="#303028", field="#20201b", hover="#414137",
        border="#68685a", foreground="#dedbc8", muted="#999786", disabled="#858373",
        selection="#c9c6b2", selection_text="#24241e", track="#4f4f41",
        alert="#e6a389", alert_surface="#4a3128",
        deviation=ClassificationPalette(
            straight=ClassificationColor("#b2b89d", "#b2b89d"),
            partial=ClassificationColor("#d8ce9e", "#d8ce9e"),
            curled=ClassificationColor("#c7b599", "#c7b599"),
            very_curled=ClassificationColor("#aaa99a", "#aaa99a"),
            nearly_closed=ClassificationColor("#c9a8b0", "#c9a8b0"),
            closed=ClassificationColor("#d0a48b", "#d0a48b"),
        ),
        destructive=ActionPalette(
            background="#c99179", foreground="#27221d", hover="#d7a48b", pressed="#b9806a",
            edges=ButtonEdges("#e0b69f", "#875b4c", "#956b56"),
        ),
        button_edges=ButtonEdges("#777463", "#171711", "#777463"),
        popup=PopupPalette("#39392f", "#898572"),
    ),
}
