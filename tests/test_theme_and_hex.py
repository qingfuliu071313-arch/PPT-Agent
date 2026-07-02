"""Tests for theme wiring and hex color normalization."""

from __future__ import annotations

import pytest

from ppt_agent.pipeline.mcp_renderer import _hex
from ppt_agent.themes import design_dna_from_theme, list_themes


@pytest.mark.parametrize("value,expected", [
    ("990033", [153, 0, 51]),
    ("#990033", [153, 0, 51]),
    ("903", [153, 0, 51]),            # 3-digit shorthand
    ("FF990033", [153, 0, 51]),       # ARGB — alpha dropped
    (" #990033 ", [153, 0, 51]),
    ("not-a-color", [0, 0, 0]),       # garbage degrades to black, no crash
    ("99003", [0, 0, 0]),             # odd length
])
def test_hex_normalization(value, expected):
    assert _hex(value) == expected


def test_every_theme_produces_a_design_dna():
    for name in list_themes():
        dna = design_dna_from_theme(name)
        assert len(dna.primary_color) == 6
        assert _hex(dna.primary_color) != [0, 0, 0] or dna.primary_color == "000000"


def test_orchestrator_uses_theme_when_no_dna():
    from ppt_agent.config import AppConfig, LLMConfig, PipelineConfig
    from ppt_agent.pipeline.orchestrator import Orchestrator

    config = AppConfig(llm=LLMConfig(provider="deepseek"), pipeline=PipelineConfig())
    orch = Orchestrator(config, theme="academic_blue")
    assert orch.dna.primary_color == "1B3A5C"
    assert orch.renderer.dna.primary_color == "1B3A5C"
