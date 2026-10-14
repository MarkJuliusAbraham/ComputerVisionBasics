"""Paint hand reports without Tk's color-keyed text antialiasing."""

from __future__ import annotations

from dataclasses import dataclass
import math

from PIL import Image, ImageFont

from gestures.hand_landmarks import FINGER_NAMES, HANDEDNESS, finger_label
from gui_tkinter.components.bars.deviation_table_layout import DeviationTableLayout, deviation_ratio
from gui_tkinter.components.overlays.fonts import OverlayFontProvider
from gui_tkinter.components.overlays.raster import AlphaCanvas
from gui_tkinter.components.theme import ThemeMetrics
from gui_tkinter.components.themes.palettes import ThemePalette
from settings.overlay_settings import OverlayStyle

from ..debug_panel.hand_summary_data import HandSummaryData
from gestures.hand_report import HandReport

from ..debug_panel.live_hand_data import LiveHandData


@dataclass(frozen=True)
class _HandLayout:
    size: tuple[int, int]
    margin: int
    gap: int
    padding: int
    line_height: int
    title_y: int
    status_y: int
    hand_top: int
    hand_bottom: int
    hand_width: int
    hand_title_y: int
    summary_y: int
    summary_row_height: int
    summary_label_width: int
    table_y: int
    fingers_y: int
    finger_row_height: int
    flank_width: int
    bar_width: int

    def hand_left(self, column: int) -> int:
        return self.margin + column * (self.hand_width + self.gap)


class HandOverlayRenderer:
    """Share report formatting and palettes; cache the static painted surface."""

    def __init__(
        self, appearance: ThemeMetrics, *, fonts: OverlayFontProvider | None = None,
    ) -> None:
        self.appearance = appearance
        self.fonts = fonts if fonts is not None else OverlayFontProvider(appearance)
        self._background: Image.Image | None = None
        self._layout: _HandLayout | None = None
        self._background_key: tuple[
            OverlayStyle, float, ThemePalette, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont, float,
        ] | None = None

    def _measure(
        self, font: ImageFont.FreeTypeFont, heading: ImageFont.FreeTypeFont,
        table: DeviationTableLayout, compact: bool,
    ) -> _HandLayout:
        pixels = self.appearance.pixels
        line = sum(font.getmetrics())
        heading_line = sum(heading.getmetrics())
        margin, gap, padding = pixels(12), pixels(16), pixels(6 if compact else 14)
        flank = math.ceil(max(font.getlength(label) for label in table.flank_labels())) + pixels(8)
        bar = pixels(table.minimum_bar_width)
        hand_width = padding * 2 + flank * 2 + pixels(8) * 2 + bar
        title_y = margin
        status_y = title_y + heading_line + pixels(8)
        hand_top = status_y + line + pixels(8 if compact else 14)
        hand_title_y = hand_top + padding
        summary_y = hand_title_y + heading_line + pixels(6 if compact else 10)
        summary_row = line + pixels(2 if compact else 8)
        table_y = summary_y + summary_row * 4 + pixels(8 if compact else 18)
        fingers_y = table_y + line + pixels(10)
        finger_row = line * 2 + pixels(4 if compact else 12)
        hand_bottom = fingers_y + finger_row * len(FINGER_NAMES) + padding
        label_width = math.ceil(max(font.getlength(label) for label, _value in HandSummaryData().fields))
        return _HandLayout(
            (margin * 2 + hand_width * 2 + gap, hand_bottom + margin),
            margin, gap, padding, line, title_y, status_y, hand_top, hand_bottom,
            hand_width, hand_title_y, summary_y, summary_row, label_width + pixels(12),
            table_y, fingers_y, finger_row, flank, bar,
        )

    def _canvas(self, image: Image.Image) -> AlphaCanvas:
        return AlphaCanvas(
            image, text_outline=self.appearance.colors.overlay_text.outline,
            text_outline_width=self.appearance.pixels(1),
        )

    def _prepare_background(
        self, style: OverlayStyle, opacity: float, palette: ThemePalette,
        font: ImageFont.FreeTypeFont, heading: ImageFont.FreeTypeFont,
        table: DeviationTableLayout,
    ) -> None:
        key = (style, opacity, palette, font, heading, self.appearance.scale)
        if key == self._background_key:
            return
        compact = style == "Simple"
        layout = self._measure(font, heading, table, compact)
        image = Image.new("RGBA", layout.size)
        canvas = self._canvas(image)
        pixels = self.appearance.pixels
        canvas.rounded_rectangle((0, 0, *layout.size), palette.surface, radius=pixels(6))
        if not compact:
            for column in range(2):
                left = layout.hand_left(column)
                box = (left, layout.hand_top, left + layout.hand_width, layout.hand_bottom)
                canvas.rounded_rectangle(box, palette.border, radius=pixels(4))
                canvas.rounded_rectangle(
                    (box[0] + 1, box[1] + 1, box[2] - 1, box[3] - 1),
                    palette.panel, radius=pixels(4),
                )
                canvas.rounded_rectangle(
                    (left + layout.padding, layout.table_y - pixels(10),
                     left + layout.hand_width - layout.padding, layout.table_y - pixels(10) + 1),
                    palette.border, radius=0,
                )
        # Apply opacity to surfaces once. Text and bars are composited afterward
        # at full opacity; overlapping cards must not make the background darker.
        image.putalpha(image.getchannel("A").point([round(value * opacity) for value in range(256)]))
        canvas.text((layout.margin, layout.title_y), "Hand tracking", heading, palette.foreground)
        for column, handedness in enumerate(HANDEDNESS):
            left = layout.hand_left(column) + layout.padding
            width = layout.hand_width - 2 * layout.padding
            canvas.text((left, layout.hand_title_y), f"{handedness} hand", heading, palette.foreground)
            for row, (label, _value) in enumerate(HandSummaryData().fields):
                canvas.text(
                    (left, layout.summary_y + row * layout.summary_row_height), label, font, palette.muted,
                )
            bar_left = left + layout.flank_width + pixels(8)
            class_left = left + width - layout.flank_width
            canvas.text((left, layout.table_y), "Finger", font, palette.muted)
            canvas.text(
                (bar_left, layout.table_y), "Deviation", font, palette.muted,
                width=layout.bar_width, align="center",
            )
            canvas.text(
                (class_left, layout.table_y), "Class", font, palette.muted,
                width=layout.flank_width, align="right",
            )
            for row, name in enumerate(FINGER_NAMES):
                top = layout.fingers_y + row * layout.finger_row_height
                canvas.text((left, top + layout.line_height // 2), finger_label(name), font, palette.foreground)
        self._background, self._layout, self._background_key = image, layout, key

    def render(
        self, data: LiveHandData, *, style: OverlayStyle, opacity: float, max_deviation: float,
    ) -> Image.Image:
        palette = self.appearance.colors.palette
        font, heading = self.fonts.font(), self.fonts.font(bold=True)
        compact = style == "Simple"
        table = DeviationTableLayout.for_report(compact=compact)
        self._prepare_background(style, opacity, palette, font, heading, table)
        assert self._background is not None and self._layout is not None
        image = self._background.copy()
        canvas = self._canvas(image)
        layout = self._layout
        canvas.text(
            (layout.margin, layout.status_y), data.tracking_status, font,
            palette.alert if data.blocking_reason else palette.muted,
            width=image.width - 2 * layout.margin,
        )
        by_hand = data.by_hand
        for column, handedness in enumerate(HANDEDNESS):
            self._draw_hand(canvas, layout, column, by_hand.get(handedness), font, palette, table, max_deviation)
        return image

    def _draw_hand(
        self, canvas: AlphaCanvas, layout: _HandLayout, column: int,
        record: HandReport | None, font: ImageFont.FreeTypeFont,
        palette: ThemePalette, table: DeviationTableLayout, max_deviation: float,
    ) -> None:
        pixels = self.appearance.pixels
        left = layout.hand_left(column) + layout.padding
        width = layout.hand_width - layout.padding * 2
        value_left = left + layout.summary_label_width
        for row, (_name, value) in enumerate(HandSummaryData.from_record(record).fields):
            canvas.text(
                (value_left, layout.summary_y + row * layout.summary_row_height), value, font,
                palette.foreground, width=width - layout.summary_label_width,
            )
        bar_left = left + layout.flank_width + pixels(8)
        class_left = left + width - layout.flank_width
        thickness = max(1, pixels(table.bar_thickness))
        fingers = record.state.fingers if record else {}
        for row, name in enumerate(FINGER_NAMES):
            finger = fingers.get(name)
            top = layout.fingers_y + row * layout.finger_row_height
            center = top + layout.line_height
            bar_top = center - thickness // 2
            canvas.rounded_rectangle(
                (bar_left, bar_top, bar_left + layout.bar_width, bar_top + thickness),
                palette.track, radius=thickness // 2,
            )
            if finger is not None:
                color = palette.deviation.color(finger.position)
                ratio = deviation_ratio(finger.deviation, max_deviation)
                canvas.rounded_rectangle(
                    (bar_left, bar_top, bar_left + round(layout.bar_width * ratio), bar_top + thickness),
                    color.fill, radius=thickness // 2,
                )
            text_color = palette.deviation.color(finger.position).text if finger else palette.foreground
            lines = table.detail_text(finger).splitlines()
            text_top = center - layout.line_height * len(lines) // 2
            for index, line in enumerate(lines):
                canvas.text(
                    (class_left, text_top + index * layout.line_height), line, font, text_color,
                    width=layout.flank_width, align="right",
                )
