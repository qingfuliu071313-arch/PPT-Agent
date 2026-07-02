"""Orchestrator: coordinates the 7-stage image-first pipeline."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from ppt_agent.config import AppConfig
from ppt_agent.llm import create_llm
from ppt_agent.models import DesignDNA, Presentation, UserRequirement
from ppt_agent.pipeline.analyzer import Analyzer
from ppt_agent.pipeline.content import ContentGenerator
from ppt_agent.pipeline.image_sourcer import ImageSourcer
from ppt_agent.pipeline.outliner import Outliner
from ppt_agent.pipeline.mcp_renderer import MCPRenderer
from ppt_agent.pipeline.validator import ContentValidator
from ppt_agent.templates import get_style_config

console = Console()


class Orchestrator:

    def __init__(
        self,
        config: AppConfig | None = None,
        design_dna: DesignDNA | None = None,
        template_path: str = "",
        theme: str = "academic_crimson",
    ):
        self.config = config or AppConfig.from_env()
        self.llm = create_llm(
            self.config.llm.provider,
            api_key=self._get_api_key(),
            model=self._get_model(),
        )
        self.analyzer = Analyzer(self.llm)
        self.outliner = Outliner(self.llm)
        self.content_gen = ContentGenerator(self.llm)
        self.image_sourcer = ImageSourcer()

        if template_path:
            from ppt_agent.template_learning import TemplateExtractor
            self.dna = TemplateExtractor().extract(template_path)
        elif design_dna:
            self.dna = design_dna
        else:
            from ppt_agent.themes import design_dna_from_theme
            self.dna = design_dna_from_theme(theme)

        self.renderer = MCPRenderer(design_dna=self.dna)

    def _get_api_key(self) -> str:
        p = self.config.llm.provider
        if p == "claude":
            return self.config.llm.claude_api_key
        if p == "deepseek":
            return self.config.llm.deepseek_api_key
        return self.config.llm.gemini_api_key

    def _get_model(self) -> str:
        p = self.config.llm.provider
        if p == "claude":
            return self.config.llm.claude_model
        if p == "deepseek":
            return self.config.llm.deepseek_model
        return self.config.llm.gemini_model

    def run(
        self,
        user_input: str,
        output_path: str = "",
        author: str = "",
    ) -> str:
        console.print(Panel("Stage 1/8: 分析需求", style="blue"))
        requirement = self.analyzer.analyze(user_input)
        console.print(f"  主题: {requirement.topic}")
        console.print(f"  场景: {requirement.scene.value}")
        console.print(f"  时长: {requirement.duration_minutes} 分钟")

        return self._run_pipeline(requirement, output_path, author, stage_offset=1)

    def run_from_requirement(
        self,
        requirement: UserRequirement,
        output_path: str = "",
        author: str = "",
    ) -> str:
        return self._run_pipeline(requirement, output_path, author, stage_offset=0)

    def _run_pipeline(
        self,
        requirement: UserRequirement,
        output_path: str,
        author: str,
        stage_offset: int,
    ) -> str:
        total_stages = stage_offset + 7

        def stage(n: int) -> str:
            return f"Stage {stage_offset + n}/{total_stages}"

        console.print(Panel(f"{stage(1)}: 模板DNA", style="blue"))
        console.print(f"  主色: #{self.dna.primary_color}")
        console.print(f"  字体: {self.dna.font_primary}")
        console.print(f"  图片占比: {self.dna.image_slide_percentage:.0%}")

        console.print(Panel(f"{stage(2)}: 生成大纲", style="blue"))
        outline = self.outliner.generate(requirement)
        console.print(f"  标题: {outline.title}")
        console.print(f"  页数: {outline.total_slides}")
        for s in outline.slides:
            console.print(f"    [{s.index}] {s.title} ({s.layout.value})")

        console.print(Panel(f"{stage(3)}: 生成内容", style="blue"))
        slides = self.content_gen.generate(requirement, outline)
        console.print(f"  已生成 {len(slides)} 页内容")
        img_count = sum(len(s.images) for s in slides)
        console.print(f"  图片规划: {img_count} 张")

        console.print(Panel(f"{stage(4)}: 获取图片", style="cyan"))
        slides = self.image_sourcer.source_all(slides)
        sourced = sum(1 for s in slides for img in s.images if img.local_path)
        console.print(f"  已获取: {sourced}/{img_count} 张图片")

        style = get_style_config(requirement.scene)

        presentation = Presentation(
            requirement=requirement,
            outline=outline,
            slides=slides,
            style=style,
            design_dna=self.dna,
            author=author,
            date=date.today().isoformat(),
        )

        console.print(Panel(f"{stage(5)}: 内容校验", style="yellow"))
        validator = ContentValidator()
        issues = validator.validate_and_fix(presentation)
        if issues:
            for issue in issues:
                tag = "[green]已修复[/green]" if issue.auto_fixed else "[red]警告[/red]"
                console.print(f"  {tag} Slide {issue.slide_index} | {issue.field}: {issue.message}")
        else:
            console.print("  ✓ 所有内容校验通过")

        console.print(Panel(f"{stage(6)}: 渲染PPT", style="blue"))

        if not output_path:
            safe_topic = requirement.topic.replace(" ", "_")[:30]
            output_dir = Path(self.config.pipeline.output_dir)
            output_path = str(output_dir / f"{safe_topic}_{date.today().isoformat()}.pptx")

        result_path = self.renderer.render(presentation, output_path)

        from ppt_agent.utils.quality_check import verify_pptx
        issues = verify_pptx(result_path, expected_slides=len(presentation.slides))
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        if errors or warnings:
            console.print(Panel("质量检查", style="yellow"))
            for issue in errors + warnings:
                tag = "[red]错误[/red]" if issue.severity == "error" else "[yellow]警告[/yellow]"
                console.print(f"  {tag} {issue}")
        else:
            console.print("  ✓ 质量检查通过")

        result_path = self._visual_qa_stage(
            presentation, result_path, stage_label=f"{stage_offset + 7}/{total_stages}"
        )

        console.print(Panel(f"完成！文件已保存到: {result_path}", style="green"))
        return result_path

    def _visual_qa_stage(self, presentation: Presentation, result_path: str,
                         stage_label: str = "8/8") -> str:
        """Render previews, report defects, auto-swap irrelevant images once."""
        console.print(Panel(f"Stage {stage_label}: 视觉QA", style="magenta"))
        try:
            from ppt_agent.pipeline.visual_qa import VisualQA

            qa = VisualQA(llm=self.llm)
            issues, pngs = qa.review(result_path, presentation)
            for issue in issues:
                style = "red" if issue.severity == "error" else "yellow"
                console.print(f"  [{style}]{issue}[/{style}]")
            if issues:
                fixed = qa.auto_fix(presentation, issues)
                if fixed:
                    console.print(f"  已自动更换 {fixed} 张图片，重新渲染...")
                    result_path = self.renderer.render(presentation, result_path)
                    remaining, pngs = qa.review(result_path, presentation)
                    console.print(f"  复检：剩余 {len(remaining)} 个问题")
            else:
                console.print("  ✓ 视觉检查通过")
            if pngs:
                console.print(f"  预览图: {pngs[0].parent}")
        except Exception as e:
            console.print(f"  [yellow]视觉QA跳过: {e}[/yellow]")
        return result_path
