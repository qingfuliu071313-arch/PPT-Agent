"""Color theme presets for academic presentations."""

from __future__ import annotations

from ppt_agent.models import DesignDNA, ThemeConfig

THEMES: dict[str, ThemeConfig] = {
    "academic_blue": ThemeConfig(
        name="学术蓝",
        primary_color="1B3A5C",
        secondary_color="F5F7FA",
        accent_color="2B6CB0",
        text_dark="1A202C",
        text_light="FFFFFF",
        text_muted="718096",
    ),
    "academic_gray": ThemeConfig(
        name="学术灰",
        primary_color="2D3748",
        secondary_color="F7F8FA",
        accent_color="B7791F",
        text_dark="1A202C",
        text_light="FFFFFF",
        text_muted="718096",
    ),
    "minimal_bw": ThemeConfig(
        name="极简黑白",
        primary_color="242424",
        secondary_color="F8F8F8",
        accent_color="EFEFEF",
        text_dark="242424",
        text_light="FFFFFF",
        text_muted="999999",
    ),
    "modern_minimal": ThemeConfig(
        name="现代极简",
        primary_color="1A1A2E",
        secondary_color="F8F9FC",
        accent_color="4A6CF7",
        text_dark="1A1A2E",
        text_light="FFFFFF",
        text_muted="8B92A5",
    ),
    "elegant_academic": ThemeConfig(
        name="典雅学术",
        primary_color="1C1C28",
        secondary_color="FAFAF8",
        accent_color="C9A96E",
        text_dark="1C1C28",
        text_light="FFFFFF",
        text_muted="8C8C8C",
    ),
    "academic_crimson": ThemeConfig(
        name="学术酒红",
        primary_color="990033",
        secondary_color="F5F5F5",
        accent_color="C00000",
        text_dark="000000",
        text_light="FFFFFF",
        text_muted="666666",
    ),
}

DEFAULT_THEME = "academic_crimson"


def get_theme(name: str) -> ThemeConfig:
    return THEMES.get(name, THEMES[DEFAULT_THEME])


def list_themes() -> list[str]:
    return list(THEMES.keys())


def design_dna_from_theme(name: str) -> DesignDNA:
    """Create a DesignDNA from a named theme preset."""
    tc = get_theme(name)
    return DesignDNA(
        name=tc.name,
        primary_color=tc.primary_color,
        secondary_color=tc.secondary_color,
        accent_color=tc.accent_color,
        text_on_primary=tc.text_light,
        text_on_light=tc.text_dark,
        text_muted=tc.text_muted,
        font_primary=tc.font_title,
        font_secondary=tc.font_body,
        frame_border_color=tc.primary_color,
    )
