"""Render smoke test: synthetic Presentation through ImageSourcer + MCPRenderer.

No LLM required. Covers every SlideLayout with realistic content so the
output can be visually inspected page by page.

Usage: .venv/bin/python tests/render_smoke.py [output.pptx]
"""

from __future__ import annotations

import sys
from datetime import date

from ppt_agent.models import (
    ChartData,
    DesignDNA,
    ImageSpec,
    Presentation,
    PresentationOutline,
    ProcessStep,
    Scene,
    SlideContent,
    SlideLayout,
    SlideOutline,
    UserRequirement,
)
from ppt_agent.pipeline.image_sourcer import ImageSourcer
from ppt_agent.pipeline.mcp_renderer import MCPRenderer


def build_slides() -> list[SlideContent]:
    return [
        SlideContent(
            index=0, layout=SlideLayout.TITLE,
            title="深度学习在医学影像分析中的应用研究",
            annotations=["博士后出站汇报"],
        ),
        SlideContent(
            index=1, layout=SlideLayout.SECTION,
            title="目录",
            annotations=["研究背景", "方法设计", "实验结果", "总结展望"],
        ),
        SlideContent(
            index=2, layout=SlideLayout.IMAGE_FOCUS,
            title="研究背景：医学影像智能分析",
            key_statement="深度学习显著提升医学影像诊断效率与准确率",
            images=[ImageSpec(
                description="CT影像示例",
                search_query="medical imaging CT scan",
                caption="胸部CT影像",
            )],
            annotations=["影像数据年增长超30%", "人工阅片耗时且易疲劳", "AI辅助诊断需求迫切",
                         "FDA已批准百余款AI影像产品", "国内三甲医院渗透率不足20%"],
            citation="Litjens et al., Medical Image Analysis, 2017",
        ),
        SlideContent(
            index=3, layout=SlideLayout.IMAGE_FOCUS,
            title="无图回退测试页",
            key_statement="该页故意不提供图片，验证全宽文本布局",
            annotations=["要点一：布局应自动转为全宽文本", "要点二：文本垂直居中分布", "要点三：不出现空占位框"],
        ),
        SlideContent(
            index=4, layout=SlideLayout.DUAL_IMAGE,
            title="传统方法 vs 深度学习方法",
            key_statement="深度学习在特征提取上具有显著优势",
            left_label="传统方法", right_label="深度学习",
            left_image=ImageSpec(
                description="传统图像处理",
                search_query="image processing edge detection example",
            ),
            right_image=ImageSpec(
                description="CNN结构",
                search_query="convolutional neural network architecture diagram",
            ),
        ),
        SlideContent(
            index=5, layout=SlideLayout.PROCESS_FLOW,
            title="技术路线",
            key_statement="四阶段渐进式研究路线",
            process_steps=[
                ProcessStep(label="数据收集", description="多中心影像数据"),
                ProcessStep(label="预处理", description="标准化与增强"),
                ProcessStep(label="模型训练", description="多任务学习框架"),
                ProcessStep(label="临床验证", description="前瞻性队列评估"),
            ],
        ),
        SlideContent(
            index=6, layout=SlideLayout.CHART,
            title="实验结果对比",
            key_statement="本方法在三个数据集上均取得最优结果",
            chart_data=ChartData(
                chart_type="column",
                categories=["数据集A", "数据集B", "数据集C"],
                series=[
                    {"name": "基线模型", "values": [82.1, 79.5, 85.0]},
                    {"name": "本文方法", "values": [91.3, 88.7, 93.2]},
                ],
                title="准确率对比 (%)",
            ),
            annotations=["平均提升8.9个百分点", "数据集C提升最显著", "推理速度保持实时"],
        ),
        SlideContent(
            index=7, layout=SlideLayout.KEY_FINDINGS,
            title="核心成果",
            key_statement="量化指标全面超越基线",
            metrics=[
                {"value": "91.3%", "label": "诊断准确率", "trend": "↑ 9.2%"},
                {"value": "0.8s", "label": "单例推理时间", "trend": "↓ 65%"},
                {"value": "3篇", "label": "SCI论文", "trend": "一区×2"},
                {"value": "2项", "label": "发明专利", "trend": "已授权"},
            ],
        ),
        SlideContent(
            index=8, layout=SlideLayout.TABLE,
            title="与现有方法对比",
            key_statement="综合性能最优",
            table_data=[
                ["方法", "准确率", "召回率", "F1", "推理时间"],
                ["ResNet-50", "82.1%", "80.3%", "81.2%", "1.2s"],
                ["ViT-Base", "86.5%", "84.9%", "85.7%", "2.3s"],
                ["本文方法", "91.3%", "90.1%", "90.7%", "0.8s"],
            ],
            citation="测试环境：NVIDIA A100, batch=1",
        ),
        SlideContent(
            index=9, layout=SlideLayout.REFERENCES,
            title="主要参考文献",
            references=[
                "[1] Litjens G, et al. A survey on deep learning in medical image analysis. Med Image Anal, 2017.",
                "[2] He K, et al. Deep residual learning for image recognition. CVPR, 2016.",
                "[3] Dosovitskiy A, et al. An image is worth 16x16 words. ICLR, 2021.",
            ],
        ),
        SlideContent(
            index=10, layout=SlideLayout.CLOSING,
            title="感谢聆听，敬请指正",
            annotations=["邮箱：demo@example.edu.cn", "课题组主页：lab.example.edu.cn"],
        ),
    ]


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "output/smoke_test.pptx"
    slides = build_slides()

    print("Sourcing images...")
    slides = ImageSourcer().source_all(slides)
    for sc in slides:
        for img in list(sc.images) + [sc.left_image, sc.right_image]:
            if img and img.search_query:
                status = img.local_path or "(missing)"
                print(f"  [{sc.index}] {img.search_query[:50]} -> {status}")

    requirement = UserRequirement(topic="深度学习医学影像", scene=Scene.THESIS_DEFENSE)
    outline = PresentationOutline(
        title="深度学习在医学影像分析中的应用研究",
        subtitle="博士后出站汇报",
        total_slides=len(slides),
        narrative_arc="背景-方法-结果-总结",
        slides=[
            SlideOutline(index=s.index, title=s.title, layout=s.layout, key_message=s.key_statement or s.title)
            for s in slides
        ],
    )
    presentation = Presentation(
        requirement=requirement, outline=outline, slides=slides,
        design_dna=DesignDNA(), author="测试用户", date=date.today().isoformat(),
    )

    print("Rendering...")
    renderer = MCPRenderer(design_dna=presentation.design_dna)
    result = renderer.render(presentation, out)
    print(f"Saved: {result}")


if __name__ == "__main__":
    main()
