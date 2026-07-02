# Academic Presentation Skill (Opus Direct + MCP, Image-First)

Create professional academic presentations. Opus generates content directly, sources real images from the web, and the DesignDNA-driven MCP renderer produces the PPTX.

## Core Philosophy: IMAGE-FIRST

Real academic PPTs are **image-centric**, not bullet-list-centric. Reference decks have ~77% of slides containing images (avg 1.9/slide); text serves as a key statement + 3-5 short annotations, never a wall of bullets. Every content slide = **one core image + one thesis statement + a few specific annotations**.

## Routing — read this first

This skill is the **working spec for the `ppt-agent` subagent**. If you are the
MAIN session assistant and the user asks to create, beautify, or modify a PPT
(做PPT / 改PPT / 美化 / 改第N页 / 换图 / 改版式 …), do NOT execute this skill
inline — spawn the agent instead: `Agent(subagent_type="ppt-agent", prompt=…)`.
Execute this skill directly only when (a) you ARE the ppt-agent subagent, or
(b) the user explicitly asks the main session to do it in-place.

## Triggers

Activate when user requests: conference talks, seminar slides, thesis defense (答辩), research presentations, lecture slides, teaching courseware (教学课件), any "make slides/PPT" paired with academic content, or modification/beautification of an existing deck (改PPT, 美化课件, 重新排版, 改某一页).

## Architecture

```
User → [learn template → DesignDNA] → Opus(content + image queries)
     → JSON → ImageSourcer(web search+download) → DNA Renderer → .pptx
```

- **Brain**: Opus generates outline + slide content directly (no external LLM API)
- **Eyes**: Wikimedia Commons + Openverse image search (keyless), curl download
- **Hands**: `ppt-agent` CLI / MCP Server tools
- **Style source**: DesignDNA extracted from a user-provided reference PPTX

## Workflow

### Step 1: Clarify Requirements

Ask user for:
- Topic and scope
- Audience (students, committee, conference attendees)
- Duration (slide count: ~1-1.5 pages/minute)
- Scene: `thesis_defense` | `work_report` | `teaching`
- **Reference PPT template** (strongly encouraged — drives all styling)
- Data sources (CSV/Excel/JSON for charts, if any)
- Author name, date

### Step 2: Learn Template DNA (if reference provided)

```bash
ppt-agent learn <reference.pptx> -o output/dna.json
```

This extracts a `DesignDNA`: primary/accent colors, font hierarchy (6 tiers),
bold ratio, alignment, header-bar geometry, content margins, and image-area
ratios — all as ratios that adapt to 16:9 / 4:3. Reuse this JSON for every
deck the user makes from that template. If no reference, the renderer falls
back to the `academic_crimson` default (#990033, Microsoft YaHei).

### Step 3: Generate Outline

Slide-by-slide plan. For each slide specify: index, title (action title —
complete sentence stating the takeaway), layout, key_message, image_plan,
annotations.

**Layout Selection Rules** (image-first, strict):
- Default → `image_focus` (should be ≥40% of slides)
- A vs B comparison → `dual_image`
- Figure needing analysis text → `figure_caption`
- Numbers/data → `chart` or `key_findings`
- Steps/process/flow → `process_flow`
- Multi-dimensional comparison (≥3 columns) → `table`
- References list → `references`
- Chapter divider → `section`
- First slide → `title`, last slide → `closing`
- **No pure-text bullet layout exists** — if tempted, use `image_focus` with a diagram

**Ghost deck test**: reading titles + key_statements alone must convey the complete argument.

### Step 4: Generate Content JSON

Match this schema (new image-first models). The authoritative field definitions
are the Pydantic models in `src/ppt_agent/models.py` — if this sketch and the
models ever disagree, the models win:

```json
{
  "requirement": {
    "topic": "...", "audience": "...", "duration_minutes": 15,
    "scene": "work_report|thesis_defense|teaching",
    "key_points": ["..."], "style_preference": "professional",
    "language": "zh", "additional_info": ""
  },
  "outline": {
    "title": "...", "subtitle": "...", "total_slides": N,
    "narrative_arc": "...",
    "slides": [
      {"index": 0, "title": "...", "layout": "title",
       "key_message": "...", "image_plan": ["..."], "annotations": ["..."]}
    ]
  },
  "slides": [
    {
      "index": 0,
      "layout": "title|section|image_focus|dual_image|figure_caption|chart|process_flow|table|key_findings|references|closing",
      "title": "Action title (complete sentence)",
      "key_statement": "One thesis sentence, 20-30 chars, shown below header",
      "images": [
        {"description": "what the image shows",
         "search_query": "english search keywords for academic image",
         "caption": "≤15 char caption"}
      ],
      "annotations": ["specific point w/ data", "method name", "quantified result"],
      "notes": "Speaker notes (200-300 chars, first-person, conversational)",
      "chart_data": {
        "chart_type": "column|bar|line|pie|doughnut   (native, editable in PPT)",
        "categories": ["..."], "series": [{"name": "...", "values": [1,2,3]}],
        "title": "...", "x_axis_title": "...", "y_axis_title": "..."
      },
      // SCIENTIFIC figures (rendered via matplotlib → DesignDNA-styled image,
      // NOT editable in PPT). Set chart_type to one of:
      //   scatter | regression | errorbar | box | violin | heatmap | hist | area
      // (or force any chart through matplotlib with "engine": "matplotlib")
      //   scatter/regression: series=[{"name":"...","x":[...],"y":[...]}]  (regression adds fit line + R²)
      //   errorbar:           series=[{"name":"...","y":[...],"yerr":[...]}] + categories
      //   box/violin/hist:    series=[{"name":"组1","values":[raw,samples,...]}, ...]
      //   heatmap:            categories=col labels, row_labels=[...], series=[{"values":[row]}, ...], optional "colormap"
      "table_data": [["H1","H2"], ["v1","v2"]],
      "process_steps": [{"label": "≤8 chars", "description": "...", "icon_search": "..."}],
      "metrics": [{"value": "95%", "label": "...", "trend": "↑ 5%"}],
      "references": ["[1] Author. Title. Journal, Year."],
      "left_image": {"description": "...", "search_query": "...", "caption": "..."},
      "right_image": {"description": "...", "search_query": "...", "caption": "..."},
      "left_label": "...", "right_label": "...",
      "citation": "source line at page bottom"
    }
  ],
  "design_dna": { /* paste contents of dna.json here, or omit for default */ },
  "author": "...", "date": "2026-06-15"
}
```

**Layout-specific required fields:**
- `image_focus`: `images` (1) + `key_statement` + `annotations` (3-5, each ≤20 chars, MUST contain concrete data/method/conclusion — never "效果显著"-type filler)
- `dual_image`: `left_image` + `right_image` + `left_label` + `right_label` + `key_statement`
- `figure_caption`: `images` (1) + `annotations` (3-5 analysis points) + `key_statement`
- `chart`: `chart_data` (real/plausible numbers!) + `key_statement` + optional `annotations` (data readout). Simple column/bar/line/pie → native editable chart; scientific figures (scatter+regression, error bars, box/violin, heatmap, hist) → matplotlib, DesignDNA-styled, image-first.
- `process_flow`: `process_steps` (3-6, label ≤8 chars) + `key_statement`
- `table`: `table_data` (first row header, 3-6 rows, 3-5 cols) + `key_statement`
- `key_findings`: `metrics` (2-4, value+label+optional trend) + `key_statement`
- `references`: `references` (numbered list)
- `section`: `annotations` (1 guiding line)
- `title`: `annotations` (1 subtitle)
- `closing`: `annotations` (["致谢", "contact"])

### Step 5: Render (image sourcing is automatic)

```bash
ppt-agent render content.json -o output.pptx --dna output/dna.json
```

The renderer's pipeline auto-sources images: for each `images`/`left_image`/
`right_image`/`process_step.icon_search`, it searches Wikimedia+Openverse,
downloads candidates, validates them as real PNG/JPEG, and falls back to a
labeled placeholder frame if nothing valid is found. `candidate_urls` are kept
on each spec for later visual-QA swaps via `ImageSourcer.resource_next()`.

For a full topic→deck run (analyze→learn→outline→content→images→validate→render):
```bash
ppt-agent generate "<topic>" -s thesis_defense -d 18 --template ref.pptx -a "作者"
```

### Step 6: QA Checklist

- [ ] Every content slide has an action title + a `key_statement`
- [ ] Ghost deck test passes (titles + key_statements tell the story)
- [ ] `image_focus`/`dual_image`/`figure_caption` ≥ 40% of slides
- [ ] Every image slide has ≥1 image spec with an english `search_query`
- [ ] Annotations: 3-5 per slide, each ≤20 chars, each carries concrete data/method/result
- [ ] Chart data: categories/series lengths match
- [ ] Process steps: 3-6, label ≤8 chars
- [ ] Table: first row header, columns aligned
- [ ] Metrics: 2-4, each value+label
- [ ] Real images embedded (verify with python-pptx: PICTURE shapes present, not all placeholders)
- [ ] Speaker notes on every content slide (200+ chars)

### Step 7: Iterate

- "改第5页的图表数据" → edit slide 5's `chart_data`, re-render
- "第3页换张图" → change `search_query`, or use `resource_next()` to swap to next candidate
- "整体配色换成深色" → re-`learn` from a different template, or edit the DNA JSON

## Design Standards

### Font Size Hierarchy (from DesignDNA, tiers)
| Tier | Default pt | Use |
|------|-----------|-----|
| big_title | 48 | Title/section/closing main text |
| header | 36 | Header-bar title |
| key_statement | 26 | Thesis line below header |
| body | 20 | Annotations |
| caption | 16 | Image captions, step labels |
| citation | 14 | Bottom citations |

When a DesignDNA is loaded, these come from the learned template, not the defaults.

### Default Theme (no template)
`academic_crimson`: primary #990033, accent #C00000, Microsoft YaHei, 1.5 line spacing, center-dominant, ~82% bold — mirrors the reference defense deck.

### Layout Rules
- 16:9 default; geometry from `DesignDNA.content_margins` (ratios)
- Header bar full-width at top, filled primary color, white centered bold title
- `key_statement` centered directly below header
- Image zone gets `image_area_ratios[layout]` of content width (≈55-70%)
- Annotations in a bordered frame beside the image

## Academic-Specific Features

### References
`references` layout, numbered list, citation-tier font. Format: `[n] Author. Title. Journal, Year.`

### Charts from data files
If user provides CSV/Excel/JSON, read the file directly (pandas or stdlib) and map columns into `chart_data` before generating the slide.

### LaTeX formulas
Render to PNG yourself via matplotlib mathtext (`plt.text(0.5, 0.5, r"$...$")` on a transparent figure), then insert as an `image_focus` image.

## Key Modules (for direct/MCP work)
- `ppt_agent.template_learning.TemplateExtractor` — PPTX → DesignDNA
- `ppt_agent.pipeline.image_sourcer.ImageSourcer` — search/download/validate images
- `ppt_agent.pipeline.mcp_renderer.MCPRenderer(design_dna=...)` — DNA-driven render
- `ppt_agent.pipeline.validator.ContentValidator` — image-first validation/auto-fix
- `ppt_agent.models.DesignDNA` — `.save_json()` / `.load_json()`
