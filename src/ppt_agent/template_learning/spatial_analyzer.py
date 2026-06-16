"""Analyze spatial layout patterns from collected shape data."""

from __future__ import annotations

from collections import Counter
from statistics import median

from pptx.util import Emu


def detect_header_bar(
    shapes: list[dict],
    slide_w: int,
    slide_h: int,
) -> dict:
    """Find a full-width colored rectangle at the top of slides — the header bar.

    Returns ratio-based geometry: {top_ratio, height_ratio, full_width}.
    """
    w_emu = slide_w
    h_emu = slide_h
    width_threshold = w_emu * 0.85

    candidates: list[dict] = []
    for sh in shapes:
        if sh["width"] >= width_threshold and sh["top"] < h_emu * 0.25:
            if sh["height"] < h_emu * 0.20:
                candidates.append(sh)

    if not candidates:
        return {"top_ratio": 0.033, "height_ratio": 0.084, "full_width": True}

    tops = [c["top"] / h_emu for c in candidates]
    heights = [c["height"] / h_emu for c in candidates]

    return {
        "top_ratio": round(median(tops), 4),
        "height_ratio": round(median(heights), 4),
        "full_width": True,
    }


def detect_content_margins(
    shapes: list[dict],
    header_bar: dict,
    slide_w: int,
    slide_h: int,
) -> dict:
    """Detect content margins by finding the bounding box of non-header shapes."""
    h_emu = slide_h
    w_emu = slide_w

    hdr_bottom_ratio = header_bar["top_ratio"] + header_bar["height_ratio"]

    content_shapes = [
        s for s in shapes
        if s["top"] / h_emu > hdr_bottom_ratio + 0.02
        and s["width"] < w_emu * 0.85
    ]

    if not content_shapes:
        return {"left": 0.06, "right": 0.06, "top": 0.16, "bottom": 0.07}

    lefts = [s["left"] / w_emu for s in content_shapes]
    rights = [(s["left"] + s["width"]) / w_emu for s in content_shapes]
    tops = [s["top"] / h_emu for s in content_shapes]
    bottoms = [(s["top"] + s["height"]) / h_emu for s in content_shapes]

    left_margin = sorted(lefts)[len(lefts) // 10] if len(lefts) > 5 else min(lefts)
    right_margin = 1.0 - (sorted(rights, reverse=True)[len(rights) // 10] if len(rights) > 5 else max(rights))
    top_margin = sorted(tops)[len(tops) // 10] if len(tops) > 5 else min(tops)
    bottom_margin = 1.0 - (sorted(bottoms, reverse=True)[len(bottoms) // 10] if len(bottoms) > 5 else max(bottoms))

    return {
        "left": round(max(0.02, left_margin), 4),
        "right": round(max(0.02, right_margin), 4),
        "top": round(max(0.10, top_margin), 4),
        "bottom": round(max(0.03, bottom_margin), 4),
    }


def compute_image_ratios(
    images: list[dict],
    all_shapes: list[dict],
    slide_w: int,
    slide_h: int,
) -> dict:
    """Compute average image-area-to-content-area ratio per slide."""
    slide_area = slide_w * slide_h
    if not slide_area:
        return {"image_focus": 0.65, "dual_image": 0.70, "figure_caption": 0.55, "process_flow": 0.40}

    slide_image_areas: dict[int, float] = {}
    for img in images:
        idx = img["slide_index"]
        area = img["width"] * img["height"]
        slide_image_areas[idx] = slide_image_areas.get(idx, 0) + area

    if not slide_image_areas:
        return {"image_focus": 0.65, "dual_image": 0.70, "figure_caption": 0.55, "process_flow": 0.40}

    ratios = [a / slide_area for a in slide_image_areas.values()]
    avg_ratio = sum(ratios) / len(ratios) if ratios else 0.5

    return {
        "image_focus": round(min(0.80, max(0.50, avg_ratio * 1.2)), 2),
        "dual_image": round(min(0.85, max(0.55, avg_ratio * 1.3)), 2),
        "figure_caption": round(min(0.70, max(0.40, avg_ratio * 1.0)), 2),
        "process_flow": round(min(0.55, max(0.30, avg_ratio * 0.7)), 2),
    }


def cluster_font_sizes(sizes: list[float]) -> dict:
    """Cluster observed font sizes into a 6-tier hierarchy."""
    if not sizes:
        return {
            "big_title": 48, "header": 36, "key_statement": 26,
            "body": 20, "caption": 16, "citation": 14,
        }

    unique = sorted(set(sizes), reverse=True)

    tiers = ["big_title", "header", "key_statement", "body", "caption", "citation"]
    result = {}

    if len(unique) >= 6:
        step = len(unique) / 6
        for i, tier in enumerate(tiers):
            idx = min(int(i * step), len(unique) - 1)
            result[tier] = int(unique[idx])
    else:
        defaults = [48, 36, 26, 20, 16, 14]
        for i, tier in enumerate(tiers):
            if i < len(unique):
                result[tier] = int(unique[i])
            else:
                result[tier] = defaults[i]

    return result


def most_common_non_neutral(colors: list[str], default: str = "990033") -> str:
    """Find most common color excluding white/black variants."""
    neutrals = {"FFFFFF", "ffffff", "000000", "F5F5F5", "f5f5f5"}
    filtered = [c for c in colors if c not in neutrals]
    if not filtered:
        return default
    return Counter(filtered).most_common(1)[0][0]


def find_text_color_on_dark(colors: list[tuple[str, str]], default: str = "FFFFFF") -> str:
    """Find text colors used on dark backgrounds."""
    text_colors = [c for c, ctx in colors if ctx == "text"]
    light_texts = []
    for c in text_colors:
        try:
            r, g, b = int(c[:2], 16), int(c[2:4], 16), int(c[4:6], 16)
            if r + g + b > 500:
                light_texts.append(c)
        except (ValueError, IndexError):
            continue
    if light_texts:
        return Counter(light_texts).most_common(1)[0][0]
    return default


def find_dark_text_color(colors: list[tuple[str, str]], default: str = "000000") -> str:
    """Find dark text colors used on light backgrounds."""
    text_colors = [c for c, ctx in colors if ctx == "text"]
    dark_texts = []
    for c in text_colors:
        try:
            r, g, b = int(c[:2], 16), int(c[2:4], 16), int(c[4:6], 16)
            if r + g + b < 300:
                dark_texts.append(c)
        except (ValueError, IndexError):
            continue
    if dark_texts:
        return Counter(dark_texts).most_common(1)[0][0]
    return default
