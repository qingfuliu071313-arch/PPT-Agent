"""Stage 2: Generate presentation outline from requirements — image-first layout selection."""

from __future__ import annotations

from ppt_agent.llm.base import BaseLLM
from ppt_agent.models import PresentationOutline, SlideLayout, SlideOutline, UserRequirement
from ppt_agent.templates import get_scene_guide

SYSTEM_PROMPT = """你是一个资深的学术演示文稿架构师。
你的设计理念是"图文并重"：每一页以图片/图表/示意图为主体，文字仅做简短注解。
每一页只传达一个核心观点，并配一张核心图片。
你必须根据内容特征选择最合适的布局类型，让信息可视化最大化。
始终返回JSON格式。"""

OUTLINE_PROMPT = """请为以下PPT需求设计大纲：

主题：{topic}
受众：{audience}
时长：{duration}分钟
场景：{scene}
要点：{key_points}
风格：{style}
补充信息：{additional_info}

{scene_guide}

=== 布局类型选择指南（图文并重） ===

你有以下11种布局可选，核心原则是每页都要有图：

1. title — 封面页。仅用于第一页。
2. section — 章节分隔页。每个大章节前用一页做过渡。
3. image_focus — ★核心布局★ 1张大图 + 关键论断 + 1-3条简短注解。
   这是最常用的布局！概念图、架构图、实验图、示意图、截图都用它。
4. dual_image — 双图对比。适合方法对比、前后对比、实验对比。
5. figure_caption — 图+分析文字。适合实验结果图+详细分析、模型图+说明。
6. chart — 数据图表页。涉及数字趋势、大小对比、占比分布就用chart。
7. process_flow — 流程图。步骤、流程、路线、阶段、推导过程。
8. table — 数据表格。多维度对比（≥3个属性）。
9. key_findings — 关键指标/概念卡。2-4个核心数字或关键概念。
10. references — 参考文献页。
11. closing — 结尾致谢页。仅用于最后一页。

=== 选择原则 ===
- 默认用 image_focus（占比应≥40%），除非有更具体的需求
- 有数据 → chart 或 key_findings
- 有步骤/流程 → process_flow
- 有A vs B对比 → dual_image
- 有实验结果图+分析 → figure_caption
- 多维度对比 → table
- 核心定义/公式 → key_findings
- ★禁止使用纯文字bullet列表布局★

请返回以下JSON格式：
{{
    "title": "演示标题",
    "subtitle": "副标题",
    "total_slides": 总页数,
    "narrative_arc": "叙事主线描述",
    "slides": [
        {{
            "index": 页码,
            "title": "页面标题（完整句子，表达核心观点）",
            "layout": "title|section|image_focus|dual_image|figure_caption|chart|process_flow|table|key_findings|references|closing",
            "key_message": "本页核心论断（一句话）",
            "image_plan": ["需要的图片描述1", "需要的图片描述2"],
            "annotations": ["简短注解1", "简短注解2"]
        }}
    ]
}}

重要：
- 根据时长控制页数：每分钟约1-2页
- image_focus布局占比应≥40%
- 每个大章节前加一页section分隔
- image_plan描述每页需要什么图片（图片搜索关键词）
- annotations最多3条，每条≤15字
- chart页的key_message中要说明图表类型
- process_flow页的annotations就是各步骤名称"""


class Outliner:

    def __init__(self, llm: BaseLLM):
        self.llm = llm

    def generate(self, requirement: UserRequirement) -> PresentationOutline:
        scene_guide = get_scene_guide(requirement.scene)
        prompt = OUTLINE_PROMPT.format(
            topic=requirement.topic,
            audience=requirement.audience,
            duration=requirement.duration_minutes,
            scene=requirement.scene.value,
            key_points="\n".join(f"- {p}" for p in requirement.key_points),
            style=requirement.style_preference,
            additional_info=requirement.additional_info,
            scene_guide=scene_guide,
        )

        data = self.llm.generate_json(prompt, system=SYSTEM_PROMPT)

        slides = []
        for s in data.get("slides", []):
            try:
                layout = SlideLayout(s.get("layout", "image_focus"))
            except ValueError:
                layout = SlideLayout.IMAGE_FOCUS

            image_plan = _parse_string_list(s.get("image_plan", []))
            annotations = _parse_string_list(s.get("annotations", []))

            slides.append(
                SlideOutline(
                    index=s.get("index", 0),
                    title=s.get("title", ""),
                    layout=layout,
                    key_message=s.get("key_message", ""),
                    image_plan=image_plan,
                    annotations=annotations,
                )
            )

        return PresentationOutline(
            title=data.get("title", requirement.topic),
            subtitle=data.get("subtitle", ""),
            total_slides=data.get("total_slides", len(slides)),
            narrative_arc=data.get("narrative_arc", ""),
            slides=slides,
        )


def _parse_string_list(raw: list) -> list[str]:
    result = []
    for item in raw:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            result.append(item.get("text", item.get("label", str(item))))
        else:
            result.append(str(item))
    return result
