"""Tests for the vectorized ink-coverage analysis."""

from __future__ import annotations

from PIL import Image, ImageDraw

from ppt_agent.pipeline.visual_qa import analyze_page_ink


def _reference_impl(png_path) -> dict:
    """The original pure-Python implementation, kept as the oracle."""
    with Image.open(png_path) as im:
        gray = im.convert("L")
        w, h = gray.size
        px = gray.load()
        ink_rows = []
        ink_total = 0
        for y in range(h):
            row_ink = 0
            for x in range(0, w, 2):
                if px[x, y] < 230:
                    row_ink += 1
            ink_rows.append(row_ink / (w / 2))
            ink_total += row_ink
        coverage = ink_total / (w / 2 * h)
        y0, y1 = int(h * 0.18), int(h * 0.93)
        max_run = 0
        run = 0
        for y in range(y0, y1):
            if ink_rows[y] < 0.01:
                run += 1
                max_run = max(max_run, run)
            else:
                run = 0
    return {"coverage": coverage, "max_blank_band": max_run / h}


def _make_page(tmp_path, name: str, draw_fn) -> str:
    img = Image.new("L", (640, 360), color=250)
    draw_fn(ImageDraw.Draw(img))
    path = tmp_path / name
    img.save(path)
    return str(path)


def test_blank_page(tmp_path):
    path = _make_page(tmp_path, "blank.png", lambda d: None)
    stats = analyze_page_ink(path)
    assert stats["coverage"] == 0.0
    assert stats["max_blank_band"] > 0.7  # whole content zone is blank


def test_dense_page(tmp_path):
    path = _make_page(
        tmp_path, "dense.png",
        lambda d: d.rectangle([0, 0, 639, 359], fill=0),
    )
    stats = analyze_page_ink(path)
    assert stats["coverage"] == 1.0
    assert stats["max_blank_band"] == 0.0


def test_matches_reference_implementation(tmp_path):
    """Vectorized version must agree with the original loop on a mixed page."""
    def draw(d):
        d.rectangle([0, 10, 639, 40], fill=30)      # header bar
        d.rectangle([50, 80, 300, 160], fill=100)   # image block
        for y in range(200, 260, 12):               # some text lines
            d.line([60, y, 500, y], fill=80, width=3)

    path = _make_page(tmp_path, "mixed.png", draw)
    got = analyze_page_ink(path)
    want = _reference_impl(path)
    assert abs(got["coverage"] - want["coverage"]) < 1e-9
    assert abs(got["max_blank_band"] - want["max_blank_band"]) < 1e-9
