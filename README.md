# PPT Agent

**AI-powered academic presentation generator — image-first, template-aware, multi-model.**
**AI 驱动的学术演示文稿生成器 —— 图文优先、模板感知、多模型。**

From a single topic sentence to a polished `.pptx` with real, relevant images: PPT Agent plans the outline, writes the content, sources figures from the open web, renders the deck through a PowerPoint MCP server, then runs a visual QA pass that can auto-swap off-topic images.

只需一句主题描述，即可得到一份配有真实、相关图片的 `.pptx`：PPT Agent 自动规划大纲、撰写内容、从开放网络检索配图，通过 PowerPoint MCP 服务器渲染，最后执行一轮视觉 QA，并能自动替换跑题的图片。

---

## Features / 功能特性

- **Image-first pipeline / 图文优先管线** — Slides are planned around figures, not bullet walls. Images are searched and downloaded before rendering.
  幻灯片围绕图片而非满屏要点来规划，图片在渲染前完成检索与下载。
- **Keyless image search / 免密钥搜图** — Sources academic-friendly imagery from Wikimedia Commons and Openverse. No image API key required.
  从 Wikimedia Commons 和 Openverse 检索适合学术的图片，无需任何图片 API 密钥。
- **Multi-model LLM / 多模型支持** — Works with Claude, Gemini, or DeepSeek. Switch with one flag.
  支持 Claude、Gemini、DeepSeek，一个参数即可切换。
- **Template learning (DesignDNA) / 模板学习** — Extract colors, fonts, and layout ratios from any reference `.pptx` and reuse them.
  从任意参考 `.pptx` 中提取配色、字体、版式比例（DesignDNA）并复用。
- **Visual QA / 视觉 QA** — Renders per-slide previews, detects layout defects, and can auto-replace irrelevant images once.
  逐页渲染预览图、检测版式缺陷，并可对不相关图片自动替换一次。
- **6 themes · 3 scenes / 6 套主题 · 3 类场景** — Academic crimson/blue/gray, minimal, elegant; work report / thesis defense / teaching.
  学术酒红/蓝/灰、极简、典雅；工作汇报 / 论文答辩 / 教学。
- **CLI + Streamlit GUI / 命令行 + 图形界面** — Use whichever fits your workflow.
  命令行与 Streamlit 图形界面任选。

---

## How it works / 工作原理

The orchestrator runs an 8-stage pipeline:
编排器执行 8 个阶段的管线：

| Stage / 阶段 | What it does / 作用 |
|---|---|
| 1. Template DNA / 模板 DNA | Load colors, fonts, layout ratios (from theme or reference `.pptx`) / 载入配色、字体、版式比例 |
| 2. Analyze / 需求分析 | Parse the user request into a structured requirement / 解析用户需求为结构化对象 |
| 3. Outline / 生成大纲 | Plan slide count, titles, and per-slide layout / 规划页数、标题与每页版式 |
| 4. Content / 生成内容 | Write text and plan image specs per slide / 撰写文本并规划每页配图 |
| 5. Source images / 获取图片 | Search + download images in parallel / 并行检索与下载图片 |
| 6. Validate / 内容校验 | Auto-fix overflow, empty fields, layout issues / 自动修复溢出、空字段、版式问题 |
| 7. Render / 渲染 | Build the `.pptx` via the PowerPoint MCP server / 通过 PowerPoint MCP 服务器生成 `.pptx` |
| 8. Visual QA / 视觉 QA | Preview, detect defects, auto-swap bad images / 预览、检测缺陷、自动替换问题图片 |

---

## Requirements / 环境要求

- **Python ≥ 3.10**
- **[uv / uvx](https://docs.astral.sh/uv/)** — used to launch the PowerPoint MCP render server on demand / 用于按需启动 PowerPoint MCP 渲染服务器
- **An LLM API key** for at least one provider / 至少一个模型的 API 密钥:
  - `ANTHROPIC_API_KEY` (Claude) · `GEMINI_API_KEY` (Gemini) · `DEEPSEEK_API_KEY` (DeepSeek)
- **(Optional) Microsoft PowerPoint or LibreOffice** — only for the `pdf` export command / 仅 `pdf` 导出命令需要
- No image API key needed — image search is keyless. / 搜图免密钥，无需图片 API。

---

## Installation / 安装

```bash
# 1. Clone / 克隆
git clone <your-repo-url>
cd PPT-Agent

# 2. Create a virtual environment / 创建虚拟环境
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install / 安装
pip install -e .                 # core / 核心
pip install -e ".[gui]"          # + Streamlit GUI / 含图形界面
pip install -e ".[dev]"          # + dev tools (pytest, ruff) / 含开发工具
```

Set your API key / 设置 API 密钥:

```bash
export DEEPSEEK_API_KEY="sk-..."     # or ANTHROPIC_API_KEY / GEMINI_API_KEY
```

> The first render downloads the `office-powerpoint-mcp-server` via `uvx` automatically.
> 首次渲染时会通过 `uvx` 自动下载 `office-powerpoint-mcp-server`。

---

## Usage / 使用方法

### CLI / 命令行

```bash
# Generate from a topic / 从主题生成
ppt-agent generate "深度学习在医学影像中的应用" \
    --provider deepseek --scene teaching --duration 20 \
    --theme academic_crimson --author "张三"

# Interactive Q&A mode / 交互问答模式
ppt-agent interactive

# Learn a DesignDNA from a reference deck / 从参考 PPT 学习 DesignDNA
ppt-agent learn reference.pptx -o output/my_dna.json

# Generate using a learned template / 用学到的模板生成
ppt-agent generate "课题汇报" --dna output/my_dna.json

# Render directly from a pre-built JSON / 直接从 JSON 渲染
ppt-agent render presentation.json -o output/deck.pptx

# Visual QA on an existing deck / 对已有 PPT 做视觉 QA
ppt-agent qa output/deck.pptx --provider claude

# Export to PDF (needs PowerPoint/LibreOffice) / 导出 PDF（需 PowerPoint/LibreOffice）
ppt-agent pdf output/deck.pptx
```

`python -m ppt_agent.cli <command>` works too. / 也可用 `python -m ppt_agent.cli <命令>`。

### GUI / 图形界面

```bash
streamlit run app.py
```

---

## Options / 常用选项

| Option / 选项 | Values / 取值 | Default / 默认 |
|---|---|---|
| `--provider`, `-p` | `claude` · `gemini` · `deepseek` | `deepseek` |
| `--scene`, `-s` | `work_report` · `thesis_defense` · `teaching` | `work_report` |
| `--theme`, `-t` | `academic_crimson` · `academic_blue` · `academic_gray` · `minimal_bw` · `modern_minimal` · `elegant_academic` | `academic_crimson` |
| `--duration`, `-d` | minutes / 分钟 | `15` |
| `--model`, `-m` | model name override / 覆盖模型名 | provider default |
| `--dna` | DesignDNA JSON path / 路径 | — |
| `--template` | reference `.pptx` path / 参考模板路径 | — |

---

## Configuration / 配置

Environment variables / 环境变量:

| Variable / 变量 | Purpose / 用途 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `GEMINI_API_KEY` | Gemini API key |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `PPT_AGENT_PROVIDER` | Default provider for `from_env` / 默认模型 |
| `PPT_AGENT_OUTPUT` | Default output directory / 默认输出目录 (`./output`) |

---

## Project structure / 项目结构

```
src/ppt_agent/
├── cli.py                 # CLI entry point / 命令行入口
├── config.py              # Config & env loading / 配置与环境变量
├── models.py              # Pydantic data models / 数据模型
├── themes.py              # Color theme presets / 主题预设
├── pipeline/              # 8-stage generation pipeline / 生成管线
│   ├── orchestrator.py    #   coordinates all stages / 阶段编排
│   ├── analyzer.py · outliner.py · content.py
│   ├── image_sourcer.py   #   image search & download / 搜图下载
│   ├── mcp_renderer.py    #   PowerPoint MCP rendering / MCP 渲染
│   ├── validator.py       #   content auto-fix / 内容自动修复
│   └── visual_qa.py       #   preview & defect detection / 预览与缺陷检测
├── llm/                   # Claude / Gemini / DeepSeek adapters / 模型适配
├── template_learning/     # DesignDNA extraction / 模板学习
├── templates/             # Scene style configs / 场景样式
└── utils/                 # image search, fonts, pdf, preview / 工具
app.py                     # Streamlit GUI / 图形界面
```

---

## Notes / 说明

- Rendering depends on the [`office-powerpoint-mcp-server`](https://pypi.org/project/office-powerpoint-mcp-server/) package, launched on demand through `uvx` (`uvx --from office-powerpoint-mcp-server ppt_mcp_server`).
  渲染依赖 `office-powerpoint-mcp-server` 包，通过 `uvx` 按需启动。
- Image relevance depends on what the open web exposes; the visual QA stage exists precisely to catch and swap weak matches.
  图片相关性取决于开放网络的可用素材；视觉 QA 阶段正是为捕捉并替换不佳匹配而设。
- Generated artifacts (`output/`, `work/`) and the virtual environment are not part of the source tree.
  生成产物（`output/`、`work/`）与虚拟环境不属于源码。

---

## License / 许可

No license specified yet. Add one before public distribution.
尚未指定许可证，公开分发前请先添加。
