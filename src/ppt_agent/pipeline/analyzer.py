"""Stage 1: Analyze user input and extract structured requirements."""

from __future__ import annotations

from ppt_agent.llm.base import BaseLLM
from ppt_agent.models import Scene, UserRequirement

SYSTEM_PROMPT = """你是一个专业的演示文稿需求分析师。
你的任务是从用户的自然语言描述中提取结构化的PPT需求。
始终返回JSON格式。"""

ANALYZE_PROMPT = """请分析以下用户需求，提取PPT制作的关键信息：

用户输入：{user_input}

请返回以下JSON格式：
{{
    "topic": "演示主题",
    "audience": "目标受众",
    "duration_minutes": 预计时长(分钟),
    "scene": "work_report 或 thesis_defense 或 teaching",
    "key_points": ["要点1", "要点2", ...],
    "style_preference": "风格偏好描述",
    "language": "zh 或 en",
    "additional_info": "其他补充信息"
}}"""


class Analyzer:

    def __init__(self, llm: BaseLLM):
        self.llm = llm

    def analyze(self, user_input: str) -> UserRequirement:
        prompt = ANALYZE_PROMPT.format(user_input=user_input)
        data = self.llm.generate_json(prompt, system=SYSTEM_PROMPT)

        scene_str = data.get("scene", "work_report")
        try:
            scene = Scene(scene_str)
        except ValueError:
            scene = Scene.WORK_REPORT

        return UserRequirement(
            topic=data.get("topic", ""),
            audience=data.get("audience", ""),
            duration_minutes=data.get("duration_minutes", 15),
            scene=scene,
            key_points=data.get("key_points", []),
            style_preference=data.get("style_preference", "professional"),
            language=data.get("language", "zh"),
            additional_info=data.get("additional_info", ""),
        )
