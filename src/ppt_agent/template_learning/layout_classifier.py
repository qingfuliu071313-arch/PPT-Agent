"""Classify template slides into SlideLayout archetypes using heuristics."""

from __future__ import annotations

from ppt_agent.models import SlideLayout


def classify_slide(
    shapes: list[dict],
    slide_w: int,
    slide_h: int,
    slide_index: int,
    total_slides: int,
) -> SlideLayout:
    """Classify a single slide based on its shape composition."""
    slide_area = slide_w * slide_h

    pictures = [s for s in shapes if s["type"] == "PICTURE"]
    text_boxes = [s for s in shapes if s["type"] in ("TEXT_BOX", "AUTO_SHAPE") and s.get("has_text")]
    charts = [s for s in shapes if s["type"] == "CHART"]
    tables = [s for s in shapes if s["type"] == "TABLE"]
    groups = [s for s in shapes if s["type"] == "GROUP"]

    total_image_area = sum(s["width"] * s["height"] for s in pictures)
    image_ratio = total_image_area / slide_area if slide_area else 0

    if slide_index == 0:
        return SlideLayout.TITLE

    if slide_index == total_slides - 1:
        return SlideLayout.CLOSING

    if charts:
        return SlideLayout.CHART

    if tables:
        return SlideLayout.TABLE

    if len(pictures) >= 2:
        return SlideLayout.DUAL_IMAGE

    if len(pictures) == 1 and image_ratio > 0.25:
        text_heavy = sum(1 for t in text_boxes if t.get("char_count", 0) > 50)
        if text_heavy > 1:
            return SlideLayout.FIGURE_CAPTION
        return SlideLayout.IMAGE_FOCUS

    if len(shapes) <= 3 and not pictures:
        large_text = [s for s in text_boxes if s.get("font_size", 0) >= 28]
        if large_text:
            return SlideLayout.SECTION

    auto_shapes = [s for s in shapes if s["type"] == "AUTO_SHAPE" and not s.get("has_text")]
    connectors = [s for s in shapes if s["type"] == "CONNECTOR"]
    if len(auto_shapes) >= 3 or connectors:
        return SlideLayout.PROCESS_FLOW

    metrics_pattern = [s for s in text_boxes if s.get("char_count", 0) < 20 and s.get("font_size", 0) >= 24]
    if len(metrics_pattern) >= 3:
        return SlideLayout.KEY_FINDINGS

    return SlideLayout.IMAGE_FOCUS
