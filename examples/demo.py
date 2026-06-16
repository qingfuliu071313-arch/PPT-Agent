"""Demo: generate a presentation programmatically."""

from ppt_agent.config import AppConfig, LLMConfig, PipelineConfig
from ppt_agent.models import Scene, UserRequirement
from ppt_agent.pipeline.orchestrator import Orchestrator


def demo_work_report():
    """Generate an academic work report presentation."""
    config = AppConfig(
        llm=LLMConfig(provider="claude"),
        pipeline=PipelineConfig(output_dir="./output"),
    )

    orchestrator = Orchestrator(config)
    result = orchestrator.run(
        "课题组月度工作汇报，面向导师和课题组成员，汇报本月的研究进展、"
        "实验结果（模型精度提升5%、完成数据集标注2000条）、遇到的学术难点以及下月计划。"
        "时长10分钟。",
        author="张三",
    )
    print(f"Work report saved to: {result}")


def demo_thesis_defense():
    """Generate a thesis defense presentation."""
    config = AppConfig(
        llm=LLMConfig(provider="claude"),
        pipeline=PipelineConfig(output_dir="./output"),
    )

    requirement = UserRequirement(
        topic="基于深度学习的中文文本情感分析研究",
        audience="答辩委员会专家",
        duration_minutes=20,
        scene=Scene.THESIS_DEFENSE,
        key_points=[
            "提出了改进的BERT情感分析模型",
            "构建了大规模中文情感语料库",
            "在多个基准测试上超越现有方法",
            "模型可解释性分析",
        ],
        style_preference="学术严谨",
        language="zh",
        additional_info="硕士学位论文答辩，导师：李教授，计算机学院",
    )

    orchestrator = Orchestrator(config)
    result = orchestrator.run_from_requirement(
        requirement,
        author="王五 | 导师：李教授",
    )
    print(f"Thesis defense saved to: {result}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "thesis":
        demo_thesis_defense()
    else:
        demo_work_report()
