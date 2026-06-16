"""Core data models for PPT Agent — image-first academic presentation architecture."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class Scene(str, Enum):
    WORK_REPORT = "work_report"
    THESIS_DEFENSE = "thesis_defense"
    TEACHING = "teaching"


class SlideLayout(str, Enum):
    TITLE = "title"
    SECTION = "section"
    IMAGE_FOCUS = "image_focus"
    DUAL_IMAGE = "dual_image"
    FIGURE_CAPTION = "figure_caption"
    TEXT_BLOCK = "text_block"
    CHART = "chart"
    PROCESS_FLOW = "process_flow"
    TABLE = "table"
    KEY_FINDINGS = "key_findings"
    REFERENCES = "references"
    CLOSING = "closing"


class ImageSpec(BaseModel):
    description: str
    search_query: str = ""
    local_path: str = ""
    caption: str = ""
    zone: str = "primary"
    candidate_urls: list[str] = Field(default_factory=list)  # unused alternates for QA swaps


class ProcessStep(BaseModel):
    label: str
    description: str = ""
    icon_search: str = ""
    icon_path: str = ""


class ChartData(BaseModel):
    chart_type: str = "column"
    categories: list[str] = Field(default_factory=list)
    series: list[dict] = Field(default_factory=list)
    title: str = ""
    x_axis_title: str = ""
    y_axis_title: str = ""


class UserRequirement(BaseModel):
    topic: str
    audience: str = ""
    duration_minutes: int = 15
    scene: Scene = Scene.WORK_REPORT
    key_points: list[str] = Field(default_factory=list)
    style_preference: str = "professional"
    language: str = "zh"
    additional_info: str = ""


class SlideOutline(BaseModel):
    index: int
    title: str
    layout: SlideLayout
    key_message: str
    image_plan: list[str] = Field(default_factory=list)
    annotations: list[str] = Field(default_factory=list)


class PresentationOutline(BaseModel):
    title: str
    subtitle: str
    total_slides: int
    narrative_arc: str
    slides: list[SlideOutline]


class SlideContent(BaseModel):
    index: int
    layout: SlideLayout
    title: str
    key_statement: str = ""
    images: list[ImageSpec] = Field(default_factory=list)
    annotations: list[str] = Field(default_factory=list)
    notes: str = ""
    chart_data: ChartData | None = None
    table_data: list[list[str]] = Field(default_factory=list)
    process_steps: list[ProcessStep] = Field(default_factory=list)
    metrics: list[dict] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    left_image: ImageSpec | None = None
    right_image: ImageSpec | None = None
    left_label: str = ""
    right_label: str = ""
    citation: str = ""


class StyleConfig(BaseModel):
    primary_color: str = "1F4E79"
    accent_color: str = "2E75B6"
    background_color: str = "FFFFFF"
    text_color: str = "333333"
    font_title: str = "Microsoft YaHei"
    font_body: str = "Microsoft YaHei"
    font_size_title: int = 28
    font_size_body: int = 18
    font_size_notes: int = 14


class ThemeConfig(BaseModel):
    name: str
    primary_color: str
    secondary_color: str
    accent_color: str
    text_dark: str = "1A202C"
    text_light: str = "FFFFFF"
    text_muted: str = "718096"
    font_title: str = "Microsoft YaHei"
    font_body: str = "Microsoft YaHei"


_DEFAULT_SIZE_HIERARCHY = {
    "big_title": 48,
    "header": 36,
    "key_statement": 26,
    "body": 20,
    "caption": 16,
    "citation": 14,
}

_DEFAULT_HEADER_BAR = {
    "top_ratio": 0.033,
    "height_ratio": 0.084,
    "full_width": True,
}

_DEFAULT_CONTENT_MARGINS = {
    "left": 0.06,
    "right": 0.06,
    "top": 0.16,
    "bottom": 0.07,
}

_DEFAULT_IMAGE_AREA_RATIOS = {
    "image_focus": 0.65,
    "dual_image": 0.70,
    "figure_caption": 0.55,
    "process_flow": 0.40,
}


class DesignDNA(BaseModel):
    name: str = "custom"

    primary_color: str = "990033"
    secondary_color: str = "F5F5F5"
    accent_color: str = "C00000"
    text_on_primary: str = "FFFFFF"
    text_on_light: str = "000000"
    text_muted: str = "666666"

    font_primary: str = "Microsoft YaHei"
    font_secondary: str = "Microsoft YaHei"
    bold_ratio: float = 0.8
    size_hierarchy: dict = Field(default_factory=lambda: dict(_DEFAULT_SIZE_HIERARCHY))
    dominant_alignment: str = "center"
    line_spacing: float = 1.5

    header_bar: dict = Field(default_factory=lambda: dict(_DEFAULT_HEADER_BAR))
    content_margins: dict = Field(default_factory=lambda: dict(_DEFAULT_CONTENT_MARGINS))

    image_area_ratios: dict = Field(default_factory=lambda: dict(_DEFAULT_IMAGE_AREA_RATIOS))

    frame_border_color: str = "990033"
    frame_border_width: float = 1.0

    avg_images_per_slide: float = 1.9
    image_slide_percentage: float = 0.77

    def to_theme_config(self) -> ThemeConfig:
        return ThemeConfig(
            name=self.name,
            primary_color=self.primary_color,
            secondary_color=self.secondary_color,
            accent_color=self.accent_color,
            text_dark=self.text_on_light,
            text_light=self.text_on_primary,
            text_muted=self.text_muted,
            font_title=self.font_primary,
            font_body=self.font_secondary,
        )

    def save_json(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, path: str | Path) -> DesignDNA:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    @classmethod
    def default_academic_crimson(cls) -> DesignDNA:
        return cls()


class Presentation(BaseModel):
    requirement: UserRequirement
    outline: PresentationOutline
    slides: list[SlideContent]
    style: StyleConfig = Field(default_factory=StyleConfig)
    design_dna: DesignDNA | None = None
    author: str = ""
    date: str = ""
