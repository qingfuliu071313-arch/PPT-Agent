"""Stage 8: Visual QA — render previews, detect defects, optionally fix.

Two tiers:
  Tier 1 (deterministic, PIL): ink coverage and empty-band analysis on the
  rendered previews. Always available, no LLM cost.
  Tier 2 (vision LLM): per-page review of image relevance, overflow,
  overlap, and overall polish. Runs when the configured LLM supports
  vision (e.g. Claude). In Opus direct mode, Claude Code reads the
  preview PNGs itself instead.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from ppt_agent.models import Presentation, SlideLayout
from ppt_agent.utils.preview import pptx_to_pngs

# Pages where large empty areas are intentional design.
_SPARSE_OK_LAYOUTS = {SlideLayout.TITLE, SlideLayout.SECTION, SlideLayout.CLOSING}


class PageIssue(BaseModel):
    slide_index: int  # 1-based page number
    severity: str = "warning"  # "error" | "warning" | "info"
    kind: str = "other"  # sparse | empty_band | image_irrelevant | overflow | overlap | other
    message: str = ""
    suggestion: str = ""

    def __str__(self) -> str:
        return f"[P{self.slide_index}|{self.severity}|{self.kind}] {self.message}"


# ── Tier 1: deterministic analysis ─────────────────────────────


def analyze_page_ink(png_path: str | Path) -> dict:
    """Measure ink coverage and the largest blank horizontal band.

    Returns {"coverage": float, "max_blank_band": float} where coverage is
    the fraction of non-background pixels and max_blank_band is the largest
    run of near-blank rows as a fraction of page height (excluding the top
    header zone and bottom footer zone).
    """
    import numpy as np
    from PIL import Image

    with Image.open(png_path) as im:
        gray = np.asarray(im.convert("L"))

    h, w = gray.shape
    ink = gray[:, ::2] < 230  # sample every 2nd pixel; darker than near-white bg
    ink_rows = ink.sum(axis=1) / (w / 2)
    coverage = float(ink.sum() / (w / 2 * h))

    # Largest blank band between 18% (below header) and 93% (above footer).
    y0, y1 = int(h * 0.18), int(h * 0.93)
    blank = ink_rows[y0:y1] < 0.01
    max_run = 0
    run = 0
    for is_blank in blank:
        if is_blank:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    max_blank_band = max_run / h

    return {"coverage": coverage, "max_blank_band": max_blank_band}


def tier1_review(png_paths: list[Path],
                 presentation: Presentation | None = None) -> list[PageIssue]:
    """Deterministic checks on rendered previews."""
    issues: list[PageIssue] = []
    for i, png in enumerate(png_paths):
        page = i + 1
        layout = None
        if presentation and i < len(presentation.slides):
            layout = presentation.slides[i].layout
        if layout in _SPARSE_OK_LAYOUTS:
            continue

        stats = analyze_page_ink(png)
        if stats["coverage"] < 0.03:
            issues.append(PageIssue(
                slide_index=page, severity="error", kind="sparse",
                message=f"页面内容过少（墨水覆盖率 {stats['coverage']:.1%}）",
                suggestion="补充内容或合并到相邻页",
            ))
        elif stats["max_blank_band"] > 0.40:
            issues.append(PageIssue(
                slide_index=page, severity="warning", kind="empty_band",
                message=f"存在大面积连续空白（{stats['max_blank_band']:.0%} 页高）",
                suggestion="增加注解条数或收缩内容区域",
            ))
    return issues


# ── Tier 2: vision LLM review ──────────────────────────────────

VISION_SYSTEM = """你是一个严格的演示文稿视觉审查专家。
你审查渲染后的幻灯片截图，找出影响专业度的视觉缺陷。
只报告确定存在的问题，不要臆测。始终返回JSON。"""

VISION_PROMPT = """请审查这页幻灯片截图（第{page}页，版式：{layout}，标题：{title}）。

逐项检查：
1. image_irrelevant: 图片内容与页面标题/主题是否明显不相关或语言不符（如外文标注图表）
2. overflow: 文字是否溢出容器、被截断
3. overlap: 元素是否重叠遮挡
4. sparse: 是否大面积空白、内容过少
5. other: 其他明显影响专业度的问题（配色冲突、图片模糊变形等）

返回JSON：
{{"issues": [{{"kind": "类型", "severity": "error|warning|info",
  "message": "问题描述（≤30字）", "suggestion": "修复建议（≤20字）"}}]}}

没有问题则返回 {{"issues": []}}"""


def tier2_review(llm, png_paths: list[Path],
                 presentation: Presentation | None = None) -> list[PageIssue]:
    """Vision-LLM page-by-page review. Requires llm.supports_vision()."""
    issues: list[PageIssue] = []
    for i, png in enumerate(png_paths):
        page = i + 1
        layout, title = "unknown", ""
        if presentation and i < len(presentation.slides):
            layout = presentation.slides[i].layout.value
            title = presentation.slides[i].title

        prompt = VISION_PROMPT.format(page=page, layout=layout, title=title)
        try:
            text = llm.generate_vision(prompt, [str(png)], system=VISION_SYSTEM)
            data = json.loads(_strip_fences(text))
        except Exception:
            continue
        for item in data.get("issues", []):
            issues.append(PageIssue(
                slide_index=page,
                severity=item.get("severity", "warning"),
                kind=item.get("kind", "other"),
                message=item.get("message", ""),
                suggestion=item.get("suggestion", ""),
            ))
    return issues


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


# ── Facade ─────────────────────────────────────────────────────


class VisualQA:
    """Render previews and run both QA tiers."""

    def __init__(self, llm=None):
        self.llm = llm

    def review(self, pptx_path: str | Path,
               presentation: Presentation | None = None,
               preview_dir: str | Path | None = None,
               ) -> tuple[list[PageIssue], list[Path]]:
        """Returns (issues, preview_png_paths)."""
        pngs = pptx_to_pngs(pptx_path, preview_dir)
        issues = tier1_review(pngs, presentation)
        if self.llm is not None and getattr(self.llm, "supports_vision", lambda: False)():
            issues.extend(tier2_review(self.llm, pngs, presentation))
        return issues, pngs

    @staticmethod
    def auto_fix(presentation: Presentation, issues: list[PageIssue]) -> int:
        """Apply deterministic fixes; returns count of fixes applied.

        Currently handles image_irrelevant: swap the slide's image to the
        next search candidate.
        """
        from ppt_agent.pipeline.image_sourcer import ImageSourcer

        sourcer = ImageSourcer()
        fixed = 0
        for issue in issues:
            if issue.kind != "image_irrelevant":
                continue
            i = issue.slide_index - 1
            if not (0 <= i < len(presentation.slides)):
                continue
            sc = presentation.slides[i]
            specs = list(sc.images) + [s for s in (sc.left_image, sc.right_image) if s]
            for spec in specs:
                if sourcer.resource_next(spec):
                    fixed += 1
                    break
        return fixed
