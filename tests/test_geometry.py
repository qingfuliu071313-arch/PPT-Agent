"""Tests for the pure geometry module."""

from __future__ import annotations

from ppt_agent.models import DesignDNA
from ppt_agent.pipeline.geometry import Geometry, fit_font_size


def test_geometry_derives_from_dna_ratios():
    dna = DesignDNA()
    geo = Geometry(dna, 13.333, 7.5)
    assert geo.W == 13.333
    assert geo.CW == geo.W - geo.M_LEFT - geo.M_RIGHT
    assert geo.BODY_Y > geo.KEY_Y > geo.HDR_TOP
    assert geo.CONTENT_BOTTOM > geo.BODY_Y
    for name in Geometry.FIELDS:
        assert isinstance(getattr(geo, name), float)


def test_geometry_respects_custom_margins():
    dna = DesignDNA(content_margins={"left": 0.10, "right": 0.10, "top": 0.16, "bottom": 0.07})
    geo = Geometry(dna, 10.0, 7.5)
    assert geo.M_LEFT == 1.0
    assert geo.CW == 8.0


def test_fit_font_size_shrinks_long_text():
    short = fit_font_size("短句", width=4.0, height=0.6, base_size=20)
    long = fit_font_size("这是一段非常长的中文注解文字" * 6, width=4.0, height=0.6, base_size=20)
    assert short == 20
    assert 10 <= long < 20


def test_fit_font_size_never_below_floor():
    size = fit_font_size("超长文本" * 200, width=1.0, height=0.3, base_size=40)
    assert size == 10
