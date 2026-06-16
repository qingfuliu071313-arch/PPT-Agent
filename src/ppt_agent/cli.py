"""Command-line interface for PPT Agent."""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel

from ppt_agent.config import AppConfig, LLMConfig, PipelineConfig
from ppt_agent.models import DesignDNA
from ppt_agent.pipeline.orchestrator import Orchestrator
from ppt_agent.themes import list_themes

console = Console()

PROVIDERS = ["claude", "gemini", "deepseek"]
THEME_CHOICES = list_themes()
SCENES = ["work_report", "thesis_defense", "teaching"]


@click.group()
def main():
    """PPT Agent - AI-powered academic presentation generator."""


@main.command()
@click.argument("template_path", type=click.Path(exists=True))
@click.option("--output", "-o", default="", help="Output DesignDNA JSON path")
def learn(template_path: str, output: str):
    """Extract DesignDNA from a reference PPTX template."""
    from ppt_agent.template_learning import TemplateExtractor

    console.print(Panel("PPT Agent - 模板学习", style="bold blue"))
    console.print(f"  分析模板: {template_path}")

    extractor = TemplateExtractor()
    dna = extractor.extract(template_path)

    console.print(f"  主色: #{dna.primary_color}")
    console.print(f"  字体: {dna.font_primary}")
    console.print(f"  粗体比例: {dna.bold_ratio:.0%}")
    console.print(f"  图片占比: {dna.image_slide_percentage:.0%}")
    console.print(f"  平均图片/页: {dna.avg_images_per_slide}")

    if not output:
        from pathlib import Path
        stem = Path(template_path).stem[:30]
        output = f"output/{stem}_dna.json"

    from pathlib import Path
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    dna.save_json(output)
    console.print(Panel(f"DesignDNA已保存: {output}", style="green"))


@main.command()
@click.argument("topic")
@click.option("--provider", "-p", default="deepseek", type=click.Choice(PROVIDERS))
@click.option("--scene", "-s", default="work_report", type=click.Choice(SCENES))
@click.option("--duration", "-d", default=15, type=int, help="Presentation duration in minutes")
@click.option("--author", "-a", default="", help="Author name")
@click.option("--output", "-o", default="", help="Output file path")
@click.option("--model", "-m", default="", help="Model name override")
@click.option("--theme", "-t", default="academic_crimson", type=click.Choice(THEME_CHOICES),
              help="Color theme (fallback if no DNA)")
@click.option("--dna", default="", help="DesignDNA JSON path")
@click.option("--template", default="", help="Reference PPTX template path")
def generate(topic: str, provider: str, scene: str, duration: int,
             author: str, output: str, model: str, theme: str,
             dna: str, template: str):
    """Generate a presentation from a topic description."""
    console.print(Panel("PPT Agent", style="bold blue",
                        subtitle=f"Provider: {provider}"))

    llm_config = LLMConfig(provider=provider)
    if model:
        if provider == "claude":
            llm_config.claude_model = model
        elif provider == "deepseek":
            llm_config.deepseek_model = model
        else:
            llm_config.gemini_model = model

    config = AppConfig(llm=llm_config, pipeline=PipelineConfig())

    design_dna = None
    if dna:
        design_dna = DesignDNA.load_json(dna)
        console.print(f"  DesignDNA: {dna}")

    user_input = f"主题：{topic}，场景：{scene}，时长：{duration}分钟"

    orchestrator = Orchestrator(
        config, design_dna=design_dna, template_path=template, theme=theme,
    )
    result = orchestrator.run(user_input, output_path=output, author=author)
    console.print(f"\nOutput: {result}")


@main.command()
@click.option("--provider", "-p", default="deepseek", type=click.Choice(PROVIDERS))
@click.option("--theme", "-t", default="academic_crimson", type=click.Choice(THEME_CHOICES))
@click.option("--dna", default="", help="DesignDNA JSON path")
@click.option("--template", default="", help="Reference PPTX template path")
def interactive(provider: str, theme: str, dna: str, template: str):
    """Interactive mode - answer questions to generate a presentation."""
    console.print(Panel("PPT Agent - 交互模式", style="bold blue"))

    topic = click.prompt("请描述你的演示主题")
    scene = click.prompt(
        "选择场景",
        type=click.Choice(SCENES),
        default="work_report",
    )
    duration = click.prompt("演示时长（分钟）", type=int, default=15)
    audience = click.prompt("目标受众", default="")
    author = click.prompt("作者姓名", default="")
    key_points = click.prompt("核心要点（用逗号分隔）", default="")
    output = click.prompt("输出路径（留空自动生成）", default="")

    parts = [f"主题：{topic}", f"场景：{scene}", f"时长：{duration}分钟"]
    if audience:
        parts.append(f"受众：{audience}")
    if key_points:
        parts.append(f"核心要点：{key_points}")
    user_input = "，".join(parts)

    config = AppConfig(llm=LLMConfig(provider=provider), pipeline=PipelineConfig())

    design_dna = DesignDNA.load_json(dna) if dna else None

    orchestrator = Orchestrator(
        config, design_dna=design_dna, template_path=template, theme=theme,
    )
    result = orchestrator.run(user_input, output_path=output, author=author)
    console.print(f"\nOutput: {result}")


@main.command()
@click.argument("json_path", type=click.Path(exists=True))
@click.option("--output", "-o", default="", help="Output file path")
@click.option("--theme", "-t", default="academic_crimson", type=click.Choice(THEME_CHOICES))
@click.option("--dna", default="", help="DesignDNA JSON path")
def render(json_path: str, output: str, theme: str, dna: str):
    """Render a PPT from a pre-generated JSON file."""
    import json
    from datetime import date
    from pathlib import Path
    from ppt_agent.models import Presentation
    from ppt_agent.pipeline.mcp_renderer import MCPRenderer
    from ppt_agent.pipeline.validator import ContentValidator

    console.print(Panel("PPT Agent - Direct Render", style="bold blue"))

    with open(json_path) as f:
        data = json.load(f)

    presentation = Presentation.model_validate(data)
    console.print(f"  标题: {presentation.outline.title}")
    console.print(f"  页数: {len(presentation.slides)}")

    console.print(Panel("内容校验", style="yellow"))
    validator = ContentValidator()
    issues = validator.validate_and_fix(presentation)
    if issues:
        for issue in issues:
            tag = "[green]已修复[/green]" if issue.auto_fixed else "[red]警告[/red]"
            console.print(f"  {tag} Slide {issue.slide_index} | {issue.field}: {issue.message}")
    else:
        console.print("  ✓ 所有内容校验通过")

    if not output:
        safe_topic = presentation.requirement.topic.replace(" ", "_")[:30]
        output = str(Path("output") / f"{safe_topic}_{date.today().isoformat()}.pptx")

    design_dna = DesignDNA.load_json(dna) if dna else presentation.design_dna

    console.print(Panel("渲染PPT", style="blue"))
    renderer = MCPRenderer(design_dna=design_dna)
    result_path = renderer.render(presentation, output)
    console.print(Panel(f"完成！文件已保存到: {result_path}", style="green"))


@main.command()
@click.argument("pptx_path", type=click.Path(exists=True))
@click.option("--preview-dir", default="", help="预览PNG输出目录（默认 <pptx>_preview/）")
@click.option("--json", "json_path", default="",
              help="Presentation JSON（提供版式信息以减少误报）")
@click.option("--provider", "-p", default="", type=click.Choice(["", *PROVIDERS]),
              help="启用 vision 审查的 LLM（如 claude；留空只跑确定性检查）")
def qa(pptx_path: str, preview_dir: str, json_path: str, provider: str):
    """Visual QA: render per-slide previews and report layout defects."""
    import json as _json
    from pathlib import Path

    from ppt_agent.models import Presentation
    from ppt_agent.pipeline.visual_qa import VisualQA

    console.print(Panel("PPT Agent - 视觉QA", style="bold magenta"))

    presentation = None
    if json_path:
        with open(json_path) as f:
            presentation = Presentation.model_validate(_json.load(f))

    llm = None
    if provider:
        from ppt_agent.llm import create_llm
        cfg = AppConfig.from_env()
        key = {
            "claude": cfg.llm.claude_api_key,
            "deepseek": cfg.llm.deepseek_api_key,
        }.get(provider, cfg.llm.gemini_api_key)
        model = {
            "claude": cfg.llm.claude_model,
            "deepseek": cfg.llm.deepseek_model,
        }.get(provider, cfg.llm.gemini_model)
        llm = create_llm(provider, api_key=key, model=model)

    out = preview_dir or f"{Path(pptx_path).with_suffix('')}_preview"
    issues, pngs = VisualQA(llm=llm).review(pptx_path, presentation, preview_dir=out)

    console.print(f"  预览图: {out}/ （{len(pngs)} 页）")
    if issues:
        for issue in issues:
            style = "red" if issue.severity == "error" else "yellow"
            console.print(f"  [{style}]{issue}[/{style}]")
        console.print(f"\n  共 {len(issues)} 个问题")
    else:
        console.print("  ✓ 确定性检查未发现问题")
    if not provider:
        console.print("  提示: 预览PNG可交给视觉模型（或 Claude Code 直接读取）做相关性/美观审查")


@main.command()
@click.argument("pptx_path", type=click.Path(exists=True))
@click.option("--output", "-o", default="", help="Output PDF path")
def pdf(pptx_path: str, output: str):
    """Export a PPTX file to PDF."""
    from ppt_agent.utils.pdf_export import export_pdf, check_pdf_support

    backend = check_pdf_support()
    if backend == "none":
        console.print("[red]No PDF backend found. Install Microsoft PowerPoint or LibreOffice.[/red]")
        return

    console.print(f"PDF backend: {backend}")
    result = export_pdf(pptx_path, output)
    if result:
        console.print(Panel(f"PDF exported: {result}", style="green"))
    else:
        console.print("[red]PDF export failed.[/red]")


if __name__ == "__main__":
    main()
