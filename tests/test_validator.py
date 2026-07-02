"""Tests for ContentValidator auto-fix logic."""

from __future__ import annotations

from ppt_agent.models import ChartData, SlideContent, SlideLayout
from ppt_agent.pipeline.validator import ContentValidator


def _slide(**kwargs) -> SlideContent:
    defaults = dict(index=1, layout=SlideLayout.IMAGE_FOCUS, title="标题", key_statement="论断")
    defaults.update(kwargs)
    return SlideContent(**defaults)


V = ContentValidator()


# ── chart fixes ──────────────────────────────────────────────

def test_fix_chart_trims_long_series():
    s = _slide(layout=SlideLayout.CHART, chart_data=ChartData(
        categories=["a", "b", "c"],
        series=[{"name": "s1", "values": [1, 2, 3, 4, 5]}],
    ))
    errs = V._validate_and_fix_slide(s)
    assert s.chart_data.series[0]["values"] == [1, 2, 3]
    assert any(e.auto_fixed and e.field == "series" for e in errs)


def test_fix_chart_pads_short_series():
    s = _slide(layout=SlideLayout.CHART, chart_data=ChartData(
        categories=["a", "b", "c"],
        series=[{"name": "s1", "values": [7]}],
    ))
    V._validate_and_fix_slide(s)
    assert s.chart_data.series[0]["values"] == [7, 0, 0]


def test_fix_chart_matching_series_untouched():
    s = _slide(layout=SlideLayout.CHART, chart_data=ChartData(
        categories=["a", "b"],
        series=[{"name": "s1", "values": [1, 2]}],
    ))
    errs = V._validate_and_fix_slide(s)
    assert s.chart_data.series[0]["values"] == [1, 2]
    assert not any(e.auto_fixed for e in errs)


# ── table fixes ──────────────────────────────────────────────

def test_fix_table_pads_and_trims_ragged_rows():
    s = _slide(layout=SlideLayout.TABLE, table_data=[
        ["h1", "h2", "h3"],
        ["a"],
        ["b1", "b2", "b3", "b4"],
    ])
    errs = V._validate_and_fix_slide(s)
    assert s.table_data[1] == ["a", "", ""]
    assert s.table_data[2] == ["b1", "b2", "b3"]
    assert sum(1 for e in errs if e.auto_fixed) == 2


# ── metrics fixes ────────────────────────────────────────────

def test_fix_metrics_fills_missing_fields():
    s = _slide(layout=SlideLayout.KEY_FINDINGS, metrics=[
        {"value": "95%"},          # missing label
        {"label": "准确率"},        # missing value
    ])
    V._validate_and_fix_slide(s)
    assert s.metrics[0]["label"]
    assert s.metrics[1]["value"] == "N/A"


# ── generic fixes ────────────────────────────────────────────

def test_fix_empty_title_and_key_statement():
    s = _slide(title="  ", key_statement="")
    errs = V._validate_and_fix_slide(s)
    assert s.title == "Slide 1"
    assert s.key_statement == s.title
    assert all(e.auto_fixed for e in errs)


def test_fix_truncates_excess_annotations():
    s = _slide(annotations=[f"注{i}" for i in range(8)])
    V._validate_and_fix_slide(s)
    assert len(s.annotations) == 5


def test_fix_process_placeholder_steps():
    s = _slide(layout=SlideLayout.PROCESS_FLOW, process_steps=[])
    V._validate_and_fix_slide(s)
    assert len(s.process_steps) == 3
