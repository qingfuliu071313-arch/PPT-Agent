"""Stage 3: Generate detailed slide content — image-first architecture."""

from __future__ import annotations

from rich.console import Console

from ppt_agent.llm.base import BaseLLM, LLMResponseError
from ppt_agent.models import (
    ChartData,
    ImageSpec,
    PresentationOutline,
    ProcessStep,
    SlideContent,
    SlideLayout,
    UserRequirement,
)

console = Console()

SYSTEM_PROMPT = """你是一个专业的学术演示文稿内容撰写专家。
你的核心理念是"图文并重"：每页以图片为主体，文字做信息饱满的注解。
你必须为每页规划核心图片，并生成图片搜索关键词。
原则：每页一个核心观点配一张核心图片，注解3-5条、每条≤20字。
注解必须具体：优先写数据、方法名、量化结论，禁止"效果显著"之类的空泛短语。
始终返回JSON格式。"""

CONTENT_PROMPT = """请为以下PPT页面生成详细内容：

演示主题：{title}
叙事主线：{narrative}
目标受众：{audience}
语言：{language}

本页信息：
- 页码：{index}
- 标题：{slide_title}
- 布局：{layout}
- 核心信息：{key_message}
- 图片规划：{image_plan}
- 注解规划：{annotations}

=== 根据布局类型生成对应字段 ===

所有布局都需要：
- title: 精炼的页面标题（标题栏显示文字）
- key_statement: 一句核心论断（居中显示在标题栏下方，20-30字）
- notes: 演讲者备注（200-300字，包含过渡语、核心讲解、时间提示）

各布局类型的专用字段：

● image_focus 布局（★最常用★）：
  - images: [{{
      "description": "图片内容描述",
      "search_query": "用于搜索图片的关键词（英文优先）",
      "caption": "图片说明文字（≤15字）"
    }}]
  - annotations: ["注解1", "注解2", ...] （3-5条，每条≤20字，含具体数据/方法/结论）

● dual_image 布局：
  - left_image: {{"description": "左图描述", "search_query": "搜索词", "caption": "说明"}}
  - right_image: {{"description": "右图描述", "search_query": "搜索词", "caption": "说明"}}
  - left_label: "左侧标签"
  - right_label: "右侧标签"

● figure_caption 布局：
  - images: [{{"description": "图片描述", "search_query": "搜索词", "caption": "说明"}}]
  - annotations: ["分析要点1", "分析要点2", "分析要点3", ...] （3-5条分析文字）

● chart 布局（必须提供真实数据！）：
  - chart_data: {{
      "chart_type": "column|bar|line|pie|doughnut|scatter|radar",
      "categories": ["类别1", "类别2", ...],
      "series": [{{"name": "系列名", "values": [数值1, 数值2, ...]}}],
      "title": "图表标题",
      "x_axis_title": "X轴标题",
      "y_axis_title": "Y轴标题"
    }}
  - annotations: ["数据解读1", "数据解读2"] （2-3条，写出具体数值对比）

● process_flow 布局：
  - process_steps: [
      {{"label": "步骤名", "description": "简短说明", "icon_search": "图标搜索词"}},
      ...
    ] （3-6个步骤，label≤8字）

● table 布局：
  - table_data: [
      ["列标题1", "列标题2", "列标题3"],
      ["数据1", "数据2", "数据3"],
      ...
    ] （第一行是表头，3-6行数据，3-5列）

● key_findings 布局：
  - metrics: [
      {{"value": "65%", "label": "指标名称", "trend": "↑ 趋势说明"}},
      ...
    ] （2-4个指标，value用大字展示）

● references 布局：
  - references: ["[1] 作者. 标题. 期刊, 年份.", ...] （参考文献列表）

● section 布局：
  - annotations: ["引导语"] （1条）

● title 布局：
  - annotations: ["副标题"]

● closing 布局：
  - annotations: ["致谢语", "联系方式"]

请返回以下JSON格式：
{{
    "index": {index},
    "layout": "{layout}",
    "title": "页面标题",
    "key_statement": "核心论断",
    "notes": "演讲者备注",
    ... 以上对应布局的专用字段 ...
}}

重要：
- 每页必须有key_statement（核心论断）
- image_focus/dual_image/figure_caption必须提供图片信息
- search_query用英文，便于搜索学术图片
- annotations 3-5条，每条≤20字，必须包含具体数字/方法名/结论，不写空泛形容
- chart布局必须提供chart_data
- process_steps每步label不超过8字
- 不要写长段文字，这是图文并重的PPT"""


class ContentGenerator:

    def __init__(self, llm: BaseLLM):
        self.llm = llm

    def generate(
        self,
        requirement: UserRequirement,
        outline: PresentationOutline,
    ) -> list[SlideContent]:
        slides = []
        for slide_outline in outline.slides:
            prompt = CONTENT_PROMPT.format(
                title=outline.title,
                narrative=outline.narrative_arc,
                audience=requirement.audience,
                language=requirement.language,
                index=slide_outline.index,
                slide_title=slide_outline.title,
                layout=slide_outline.layout.value,
                key_message=slide_outline.key_message,
                image_plan=", ".join(slide_outline.image_plan) if slide_outline.image_plan else "无特定图片规划",
                annotations=", ".join(slide_outline.annotations) if slide_outline.annotations else "无预设注解",
            )

            try:
                data = self.llm.generate_json(prompt, system=SYSTEM_PROMPT)
            except LLMResponseError as e:
                # Degrade to the outline plan instead of discarding all prior slides.
                console.print(
                    f"  [yellow]第 {slide_outline.index} 页内容生成失败（{e}），"
                    f"回退到大纲内容[/yellow]"
                )
                data = {}

            try:
                layout = SlideLayout(data.get("layout", slide_outline.layout.value))
            except ValueError:
                layout = slide_outline.layout

            slides.append(
                SlideContent(
                    index=data.get("index") or slide_outline.index,
                    layout=layout,
                    title=data.get("title") or slide_outline.title,
                    key_statement=data.get("key_statement") or slide_outline.key_message,
                    images=_parse_images(data.get("images")),
                    annotations=data.get("annotations") or [],
                    notes=data.get("notes") or "",
                    chart_data=_parse_chart(data.get("chart_data")),
                    table_data=data.get("table_data") or [],
                    process_steps=_parse_process_steps(data.get("process_steps")),
                    metrics=data.get("metrics") or [],
                    references=data.get("references") or [],
                    left_image=_parse_single_image(data.get("left_image")),
                    right_image=_parse_single_image(data.get("right_image")),
                    left_label=data.get("left_label") or "",
                    right_label=data.get("right_label") or "",
                    citation=data.get("citation") or "",
                )
            )

        return slides


def _parse_images(raw: list | None) -> list[ImageSpec]:
    if not raw:
        return []
    result = []
    for item in raw:
        if isinstance(item, dict):
            result.append(ImageSpec(
                description=item.get("description", ""),
                search_query=item.get("search_query", ""),
                caption=item.get("caption", ""),
                zone=item.get("zone", "primary"),
            ))
    return result


def _parse_single_image(raw: dict | None) -> ImageSpec | None:
    if not raw or not isinstance(raw, dict):
        return None
    return ImageSpec(
        description=raw.get("description", ""),
        search_query=raw.get("search_query", ""),
        caption=raw.get("caption", ""),
        zone=raw.get("zone", "primary"),
    )


def _parse_chart(raw: dict | None) -> ChartData | None:
    if not raw or not isinstance(raw, dict):
        return None
    return ChartData(
        chart_type=raw.get("chart_type", "column"),
        categories=raw.get("categories", []),
        series=raw.get("series", []),
        title=raw.get("title", ""),
        x_axis_title=raw.get("x_axis_title", ""),
        y_axis_title=raw.get("y_axis_title", ""),
    )


def _parse_process_steps(raw: list | None) -> list[ProcessStep]:
    if not raw:
        return []
    result = []
    for item in raw:
        if isinstance(item, dict):
            result.append(ProcessStep(
                label=item.get("label", ""),
                description=item.get("description", ""),
                icon_search=item.get("icon_search", ""),
            ))
        elif isinstance(item, str):
            result.append(ProcessStep(label=item))
    return result
