"""Scene-specific templates and style presets."""

from ppt_agent.models import Scene, StyleConfig
from ppt_agent.templates.work_report import WORK_REPORT_GUIDE, WORK_REPORT_STYLE
from ppt_agent.templates.thesis_defense import THESIS_DEFENSE_GUIDE, THESIS_DEFENSE_STYLE
from ppt_agent.templates.teaching import TEACHING_GUIDE, TEACHING_STYLE


def get_scene_guide(scene: Scene) -> str:
    guides = {
        Scene.WORK_REPORT: WORK_REPORT_GUIDE,
        Scene.THESIS_DEFENSE: THESIS_DEFENSE_GUIDE,
        Scene.TEACHING: TEACHING_GUIDE,
    }
    return guides.get(scene, "")


def get_style_config(scene: Scene) -> StyleConfig:
    styles = {
        Scene.WORK_REPORT: WORK_REPORT_STYLE,
        Scene.THESIS_DEFENSE: THESIS_DEFENSE_STYLE,
        Scene.TEACHING: TEACHING_STYLE,
    }
    return styles.get(scene, StyleConfig())


__all__ = ["get_scene_guide", "get_style_config"]
