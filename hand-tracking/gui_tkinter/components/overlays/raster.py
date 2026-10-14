"""Small alpha-aware drawing operations shared by raster overlay views."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from PIL import Image, ImageColor, ImageDraw, ImageFont


class AlphaCanvas:
    def __init__(
        self, image: Image.Image, *, text_outline: str | None = None, text_outline_width: int = 1,
    ) -> None:
        self.image = image
        self.text_outline = text_outline
        self.text_outline_width = max(1, text_outline_width)

    @staticmethod
    @lru_cache(maxsize=128)
    def _rounded_mask(width: int, height: int, radius: int, opacity: int) -> Image.Image:
        mask = Image.new("L", (width * 2, height * 2))
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, width * 2 - 1, height * 2 - 1), radius=radius * 2, fill=opacity,
        )
        return mask.resize((width, height), Image.Resampling.LANCZOS)

    def rounded_rectangle(
        self, box: tuple[int, int, int, int], color: str, *, radius: int, opacity: float = 1.0,
    ) -> None:
        left, top, right, bottom = box
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            return
        mask = self._rounded_mask(width, height, radius, round(opacity * 255))
        self._composite(mask, color, (left, top))

    def text(
        self, position: tuple[int, int], text: str, font: ImageFont.FreeTypeFont,
        color: str, *, width: int | None = None, align: Literal["left", "center", "right"] = "left",
    ) -> None:
        if width is not None:
            text = self.fit_text(text, font, width)
        left, top = position
        if width is not None:
            spare = width - round(font.getlength(text))
            left += spare // 2 if align == "center" else spare if align == "right" else 0
        # Grayscale coverage avoids ClearType's colored subpixels, which need
        # a known opaque background. RGB never contains a transparency key.
        mask, offset = self._text_mask(text, font)
        if mask is not None:
            if self.text_outline is not None:
                outline, outline_offset = self._text_mask(text, font, self.text_outline_width)
                if outline is not None:
                    # This local contrast surface stays opaque at every slider
                    # value, including beneath partially covered glyph edges.
                    self._composite(
                        outline, self.text_outline,
                        (left + outline_offset[0], top + outline_offset[1]),
                    )
            self._composite(mask, color, (left + offset[0], top + offset[1]))

    @staticmethod
    @lru_cache(maxsize=512)
    def _text_mask(
        text: str, font: ImageFont.FreeTypeFont, stroke_width: int = 0,
    ) -> tuple[Image.Image | None, tuple[int, int]]:
        mask_data, offset = font.getmask2(
            text, mode="L", anchor="lt", stroke_width=stroke_width, stroke_filled=True,
        )
        mask = (
            Image.frombytes("L", mask_data.size, bytes(mask_data))
            if mask_data.size[0] and mask_data.size[1] else None
        )
        return mask, offset

    @staticmethod
    @lru_cache(maxsize=512)
    def fit_text(text: str, font: ImageFont.FreeTypeFont, width: int) -> str:
        if font.getlength(text) <= width:
            return text
        suffix = "…"
        if font.getlength(suffix) > width:
            return ""
        low, high = 0, len(text)
        while low < high:
            middle = (low + high + 1) // 2
            if font.getlength(text[:middle] + suffix) <= width:
                low = middle
            else:
                high = middle - 1
        return text[:low] + suffix

    def _composite(self, mask: Image.Image, color: str, position: tuple[int, int]) -> None:
        ink = Image.new("RGBA", mask.size, (*ImageColor.getrgb(color), 255))
        ink.putalpha(mask)
        self.image.alpha_composite(ink, position)
