"""Pure geometry and color math derived from DesignDNA — no MCP dependency."""

from __future__ import annotations

from ppt_agent.models import DesignDNA


def hex_to_rgb(color: str) -> list[int]:
    h = color.strip().lstrip("#")
    if len(h) == 3:  # shorthand, e.g. "903"
        h = "".join(c * 2 for c in h)
    elif len(h) == 8:  # ARGB from template themes — drop alpha
        h = h[2:]
    if len(h) != 6:
        return [0, 0, 0]
    try:
        return [int(h[i : i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        return [0, 0, 0]


def lighten(rgb: list[int], factor: float = 0.3) -> list[int]:
    return [min(255, int(c + (255 - c) * factor)) for c in rgb]


def fit_font_size(text: str, width: float, height: float, base_size: int) -> int:
    """Shrink the font until the text plausibly fits the box (rough CJK-aware model)."""
    cjk = sum(1 for c in text if ord(c) > 0x2E80)
    latin = len(text) - cjk
    char_width = cjk * 1.0 + latin * 0.55
    chars_per_line = max(1, width * 72 / base_size)
    lines_needed = max(1, char_width / chars_per_line)
    line_height = base_size * 1.5 / 72
    total_height = lines_needed * line_height

    size = base_size
    while total_height > height * 1.1 and size > 10:
        size -= 1
        chars_per_line = max(1, width * 72 / size)
        lines_needed = max(1, char_width / chars_per_line)
        line_height = size * 1.5 / 72
        total_height = lines_needed * line_height

    return size


def aspect_fit(image_path: str, left: float, top: float,
               w: float, h: float) -> tuple[float, float, float, float]:
    """Fit the image inside the box preserving aspect ratio, centered."""
    try:
        from PIL import Image

        with Image.open(image_path) as im:
            iw, ih = im.size
        scale = min(w / iw, h / ih)
        fw, fh = iw * scale, ih * scale
        return left + (w - fw) / 2, top + (h - fh) / 2, fw, fh
    except Exception:
        return left, top, w, h


class Geometry:
    """All layout positions derived from DesignDNA ratios for a page size."""

    def __init__(self, dna: DesignDNA, width: float, height: float):
        self.W = width
        self.H = height
        self.HDR_TOP = height * dna.header_bar.get("top_ratio", 0.033)
        self.HDR_H = height * dna.header_bar.get("height_ratio", 0.084)
        self.M_LEFT = width * dna.content_margins.get("left", 0.06)
        self.M_RIGHT = width * dna.content_margins.get("right", 0.06)
        self.CONTENT_TOP = height * dna.content_margins.get("top", 0.16)
        self.CONTENT_BOTTOM = height * (1 - dna.content_margins.get("bottom", 0.07))
        self.CW = width - self.M_LEFT - self.M_RIGHT
        self.CH = self.CONTENT_BOTTOM - self.CONTENT_TOP
        self.CITE_Y = height - 0.55
        self.KEY_Y = self.HDR_TOP + self.HDR_H + 0.12
        self.KEY_H = 0.65
        self.BODY_Y = self.KEY_Y + self.KEY_H + 0.1
        self.BODY_H = self.CONTENT_BOTTOM - self.BODY_Y

    FIELDS = (
        "W", "H", "HDR_TOP", "HDR_H", "M_LEFT", "M_RIGHT",
        "CONTENT_TOP", "CONTENT_BOTTOM", "CW", "CH",
        "CITE_Y", "KEY_Y", "KEY_H", "BODY_Y", "BODY_H",
    )
