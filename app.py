"""Streamlit GUI for the academic PPT agent.

Wraps the existing pipeline (template learning -> content -> image sourcing ->
DNA-driven render -> visual QA preview) in a visual shell. No core logic is
reimplemented here; this is an orchestration + state-management layer.

Run:  streamlit run app.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from ppt_agent.models import DesignDNA, Presentation  # noqa: E402
from ppt_agent.template_learning import TemplateExtractor  # noqa: E402
from ppt_agent.pipeline.image_sourcer import ImageSourcer  # noqa: E402
from ppt_agent.pipeline.mcp_renderer import MCPRenderer  # noqa: E402
from ppt_agent.pipeline.validator import ContentValidator  # noqa: E402
from ppt_agent.pipeline.visual_qa import tier1_review  # noqa: E402
from ppt_agent.utils.preview import pptx_to_pngs  # noqa: E402

WORK_DIR = Path(tempfile.gettempdir()) / "ppt_agent_gui"
WORK_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="学术PPT生成器", page_icon="📊", layout="wide")


# ── state helpers ──────────────────────────────────────────────

def _init_state() -> None:
    st.session_state.setdefault("dna", None)          # DesignDNA
    st.session_state.setdefault("pres", None)         # Presentation
    st.session_state.setdefault("pptx_path", "")      # rendered file
    st.session_state.setdefault("pngs", [])           # preview PNG paths
    st.session_state.setdefault("dirty", False)       # needs re-render


def _save_uploaded(uploaded, suffix: str) -> str:
    dest = WORK_DIR / f"upload_{uploaded.name}"
    dest.write_bytes(uploaded.getbuffer())
    return str(dest)


# ── tabs ───────────────────────────────────────────────────────

def tab_template() -> None:
    st.subheader("① 模板 DNA")
    st.caption("上传一份参考 PPTX，提取其设计 DNA（配色 / 字体 / 版式比例）；也可不传，用默认学术酒红。")

    col_u, col_d = st.columns([1, 1])
    with col_u:
        up = st.file_uploader("参考模板 (.pptx)", type=["pptx"], key="tpl_upload")
        if up and st.button("🔍 学习这个模板", width="stretch"):
            path = _save_uploaded(up, ".pptx")
            with st.spinner("分析模板中…"):
                st.session_state.dna = TemplateExtractor().extract(path)
            st.success("已提取 DesignDNA")
    with col_d:
        if st.button("使用默认（学术酒红 #990033）", width="stretch"):
            st.session_state.dna = DesignDNA()
            st.success("已载入默认 DNA")

    dna: DesignDNA | None = st.session_state.dna
    if dna is None:
        st.info("尚未载入 DNA。上传模板或点默认。")
        return

    st.divider()
    st.markdown("**可微调的设计 DNA**（改完会用于渲染）")
    c1, c2, c3 = st.columns(3)
    with c1:
        dna.primary_color = st.color_picker("主色", f"#{dna.primary_color}").lstrip("#").upper()
        dna.accent_color = st.color_picker("强调色", f"#{dna.accent_color}").lstrip("#").upper()
        dna.frame_border_color = st.color_picker("边框色", f"#{dna.frame_border_color}").lstrip("#").upper()
    with c2:
        dna.text_on_primary = st.color_picker("页眉文字", f"#{dna.text_on_primary}").lstrip("#").upper()
        dna.text_on_light = st.color_picker("正文文字", f"#{dna.text_on_light}").lstrip("#").upper()
        dna.font_primary = st.text_input("主字体", dna.font_primary)
    with c3:
        st.metric("粗体比例", f"{dna.bold_ratio:.0%}")
        st.metric("图片页占比", f"{dna.image_slide_percentage:.0%}")
        st.metric("平均图片/页", f"{dna.avg_images_per_slide}")

    st.caption(
        f"字号层级: 大标题 {dna.size_hierarchy.get('big_title')} / "
        f"页眉 {dna.size_hierarchy.get('header')} / 论断 {dna.size_hierarchy.get('key_statement')} / "
        f"正文 {dna.size_hierarchy.get('body')} ｜ 对齐 {dna.dominant_alignment} ｜ 行距 {dna.line_spacing}"
    )


def tab_content() -> None:
    st.subheader("② 内容")
    st.caption("载入演示内容 JSON（由 Opus 在 Claude Code 中生成），或在配置了 API key 时从主题直接生成。")

    mode = st.radio("内容来源", ["上传 / 粘贴 JSON", "从主题生成 (需 LLM API key)"], horizontal=True)

    if mode.startswith("上传"):
        up = st.file_uploader("演示内容 (.json)", type=["json"], key="json_upload")
        pasted = st.text_area("或直接粘贴 JSON", height=200, placeholder='{"requirement": ..., "outline": ..., "slides": [...]}')
        if st.button("✅ 载入内容"):
            raw = None
            if up:
                raw = up.getvalue().decode("utf-8")
            elif pasted.strip():
                raw = pasted
            if not raw:
                st.error("请上传或粘贴 JSON")
                return
            try:
                data = json.loads(raw)
                pres = Presentation.model_validate(data)
            except Exception as e:  # noqa: BLE001
                st.error(f"解析失败: {e}")
                return
            issues = ContentValidator().validate_and_fix(pres)
            st.session_state.pres = pres
            st.session_state.dirty = True
            st.success(f"已载入 {len(pres.slides)} 页｜校验自动修复 {sum(1 for i in issues if i.auto_fixed)} 项")
    else:
        _topic_generate_ui()

    _outline_editor()


def _topic_generate_ui() -> None:
    import os
    topic = st.text_input("主题", placeholder="深度学习在医学影像中的应用")
    c1, c2, c3 = st.columns(3)
    scene = c1.selectbox("场景", ["thesis_defense", "work_report", "teaching"])
    duration = c2.slider("时长(分钟)", 5, 40, 18)
    provider = c3.selectbox("LLM", ["deepseek", "claude", "gemini"])
    key_env = {"deepseek": "DEEPSEEK_API_KEY", "claude": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}[provider]
    if not os.environ.get(key_env):
        st.warning(f"未检测到 {key_env}。从主题生成需要该 API key；无 key 请改用「上传 JSON」（Opus 直连模式的标准流程）。")
        return
    if st.button("🚀 生成内容") and topic:
        from ppt_agent.config import AppConfig, LLMConfig, PipelineConfig
        from ppt_agent.pipeline.analyzer import Analyzer
        from ppt_agent.pipeline.outliner import Outliner
        from ppt_agent.pipeline.content import ContentGenerator
        from ppt_agent.llm import create_llm
        from datetime import date
        cfg = AppConfig(llm=LLMConfig(provider=provider), pipeline=PipelineConfig())
        llm = create_llm(provider, api_key=os.environ[key_env], model="")
        with st.spinner("生成大纲与内容中…"):
            req = Analyzer(llm).analyze(f"主题：{topic}，场景：{scene}，时长：{duration}分钟")
            outline = Outliner(llm).generate(req)
            slides = ContentGenerator(llm).generate(req, outline)
        pres = Presentation(requirement=req, outline=outline, slides=slides,
                            design_dna=st.session_state.dna, date=date.today().isoformat())
        ContentValidator().validate_and_fix(pres)
        st.session_state.pres = pres
        st.session_state.dirty = True
        st.success(f"已生成 {len(slides)} 页")


def _outline_editor() -> None:
    pres: Presentation | None = st.session_state.pres
    if pres is None:
        return
    st.divider()
    st.markdown(f"**大纲**　{pres.outline.title}（{len(pres.slides)} 页）")
    rows = [
        {"#": sc.index, "标题": sc.title, "版式": sc.layout.value,
         "核心论断": sc.key_statement, "图片数": len(sc.images) + bool(sc.left_image) + bool(sc.right_image)}
        for sc in pres.slides
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def tab_render() -> None:
    st.subheader("③ 渲染 & 预览")
    pres: Presentation | None = st.session_state.pres
    dna: DesignDNA | None = st.session_state.dna
    if pres is None:
        st.info("请先在「内容」标签载入演示内容。")
        return
    if dna is None:
        dna = pres.design_dna or DesignDNA()

    c1, c2 = st.columns([1, 1])
    fetch = c1.checkbox("渲染前联网配图", value=True,
                        help="为每页的图片规划搜索/下载真实图片（Wikimedia/Openverse）")
    if c2.button("🎬 渲染并生成预览", type="primary", width="stretch"):
        if fetch:
            with st.spinner("联网配图中…"):
                pres.slides = ImageSourcer().source_all(pres.slides)
        out = str(WORK_DIR / "deck.pptx")
        with st.spinner("渲染 PPTX 中…（首次会拉起 MCP server，稍慢）"):
            MCPRenderer(design_dna=dna).render(pres, out)
        with st.spinner("生成预览图…"):
            pngs = pptx_to_pngs(out, str(WORK_DIR / "preview"), dpi=110)
        st.session_state.pptx_path = out
        st.session_state.pngs = [str(p) for p in pngs]
        st.session_state.dirty = False
        st.success(f"完成：{len(pngs)} 页")

    pngs = st.session_state.pngs
    if not pngs:
        return

    # Tier1 deterministic QA
    issues = tier1_review([Path(p) for p in pngs], pres)
    if issues:
        with st.expander(f"⚠ 自动检查发现 {len(issues)} 项", expanded=True):
            for iss in issues:
                st.write(f"- {iss}")
    else:
        st.caption("✓ Tier1 自动检查通过")

    st.divider()
    cols = st.columns(3)
    for i, png in enumerate(pngs):
        with cols[i % 3]:
            st.image(png, caption=f"第 {i + 1} 页", width="stretch")

    st.divider()
    d1, d2 = st.columns(2)
    with open(st.session_state.pptx_path, "rb") as f:
        d1.download_button("⬇ 下载 .pptx", f, file_name="presentation.pptx",
                           width="stretch")
    pdf = Path(st.session_state.pptx_path).with_suffix(".pdf")
    if pdf.exists():
        with open(pdf, "rb") as f:
            d2.download_button("⬇ 下载 PDF", f, file_name="presentation.pdf",
                               width="stretch")


def tab_images() -> None:
    st.subheader("④ 配图微调")
    pres: Presentation | None = st.session_state.pres
    if pres is None or not st.session_state.pngs:
        st.info("先在「渲染 & 预览」里渲染一次，配图后才有候选可换。")
        return

    sourcer = ImageSourcer()
    swapped = False
    for sc in pres.slides:
        specs = [("主图", s) for s in sc.images]
        if sc.left_image:
            specs.append(("左图", sc.left_image))
        if sc.right_image:
            specs.append(("右图", sc.right_image))
        if not specs:
            continue
        st.markdown(f"**第 {sc.index} 页** · {sc.title}")
        for label, spec in specs:
            c1, c2 = st.columns([2, 3])
            with c1:
                if spec.local_path and Path(spec.local_path).exists():
                    st.image(spec.local_path, caption=f"{label}: {spec.description}", width=220)
                else:
                    st.write(f"{label}: （无图）")
            with c2:
                st.caption(f"搜索词: `{spec.search_query}`　备选 {len(spec.candidate_urls)} 张")
                if spec.candidate_urls and st.button(
                    f"🔄 换下一张", key=f"swap_{sc.index}_{label}_{id(spec)}"
                ):
                    if sourcer.resource_next(spec):
                        swapped = True
                        st.session_state.dirty = True
        st.divider()

    if swapped:
        st.warning("已替换图片，请回到「渲染 & 预览」重新渲染查看效果。")
    elif st.session_state.dirty:
        st.info("有改动待重渲染。")


# ── main ───────────────────────────────────────────────────────

def main() -> None:
    _init_state()

    with st.sidebar:
        st.title("📊 学术PPT生成器")
        st.caption("图文并重 · 模板学习 · 视觉QA")
        st.divider()
        dna = st.session_state.dna
        pres = st.session_state.pres
        st.write("**状态**")
        st.write(f"- DNA: {'✅ ' + ('#' + dna.primary_color if dna else '') if dna else '❌ 未载入'}")
        st.write(f"- 内容: {'✅ ' + str(len(pres.slides)) + ' 页' if pres else '❌ 未载入'}")
        st.write(f"- 渲染: {'✅ 已生成' if st.session_state.pngs else '❌ 未渲染'}")
        if st.session_state.dirty and st.session_state.pngs:
            st.warning("有改动待重渲染")
        st.divider()
        st.caption("用法：① 选 DNA → ② 载入内容 → ③ 渲染预览 → ④ 微调配图")

    t1, t2, t3, t4 = st.tabs(["① 模板 DNA", "② 内容", "③ 渲染 & 预览", "④ 配图微调"])
    with t1:
        tab_template()
    with t2:
        tab_content()
    with t3:
        tab_render()
    with t4:
        tab_images()


if __name__ == "__main__":
    main()
