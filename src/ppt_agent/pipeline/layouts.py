"""Slide layout builders — one async function per SlideLayout.

Each builder receives the renderer `r` (drawing primitives + geometry
attributes derived from DesignDNA), the MCP client `s`, the slide content
`sc`, and the full presentation `pres`; it returns the new slide index.
"""

from __future__ import annotations

from pathlib import Path

from ppt_agent.models import ImageSpec, Presentation, SlideContent, SlideLayout
from ppt_agent.pipeline.geometry import lighten
from ppt_agent.utils import charts


async def slide_title(r, s, sc: SlideContent, pres: Presentation) -> int:
    idx = await r._blank(s)

    await r._rect(s, idx, 0, 0, r.W, 0.12, r._primary)

    if sc.annotations:
        await r._text(s, idx, 0, 1.15, r.W, 0.5,
                      sc.annotations[0], size=r._sz("caption") + 2,
                      bold=False, color=r._text_muted, align="center")

    await r._text(s, idx, 0.8, 2.1, r.W - 1.6, 1.9,
                  sc.title, size=r._sz("big_title"), bold=True,
                  color=r._primary, align="center")

    await r._rect(s, idx, r.W / 2 - 0.9, 4.25, 1.8, 0.05, r._accent)

    meta_parts = []
    if pres.author:
        meta_parts.append(pres.author)
    if pres.date:
        meta_parts.append(pres.date)
    if meta_parts:
        await r._text(s, idx, 0, 4.6, r.W, 1.4,
                      "\n".join(meta_parts), size=r._sz("body"),
                      bold=False, color=r._text_muted, align="center")

    await r._rect(s, idx, 0, r.H - 0.85, r.W, 0.85, r._primary)

    return idx


async def slide_section(r, s, sc: SlideContent, pres: Presentation) -> int:
    idx = await r._blank(s)
    r._section_num += 1

    await r._rect(s, idx, 0, 0, 0.25, r.H, r._primary)

    await r._text(s, idx, 0.9, 1.0, 2.8, 1.7,
                  f"{r._section_num:02d}", size=80, bold=True,
                  color=r._primary)

    await r._text(s, idx, 3.2, 1.35, r.W - 4.2, 1.3,
                  sc.title, size=r._sz("big_title") - 8, bold=True,
                  color=r._text_on_light)

    if sc.annotations:
        await r._text(s, idx, 3.2, 2.5, r.W - 4.2, 0.5,
                      sc.annotations[0], size=r._sz("caption") + 2,
                      bold=False, color=r._text_muted)

    await r._rect(s, idx, 0.9, 3.15, r.W - 2.0, 0.025,
                  lighten(r._primary, 0.6))

    # Agenda: current section highlighted, others muted.
    sections = []
    sec_num = 0
    for so in (pres.outline.slides if pres.outline else []):
        if so.layout == SlideLayout.SECTION:
            sec_num += 1
            sections.append((sec_num, so.title))
    y = 3.6
    for num, title in sections[:6]:
        current = num == r._section_num
        marker = "▸ " if current else ""
        await r._text(s, idx, 1.2, y, r.W - 2.6, 0.5,
                      f"{marker}{num:02d}  {title}",
                      size=r._sz("body") + (2 if current else 0),
                      bold=current,
                      color=r._primary if current else r._text_muted)
        y += 0.58

    return idx


async def slide_image_focus(r, s, sc: SlideContent, pres: Presentation) -> int:
    idx = await r._blank(s)
    await r._header_band(s, idx, sc.title)
    await r._key_statement(s, idx, sc.key_statement)

    img_spec = sc.images[0] if sc.images else None
    has_img = bool(img_spec and img_spec.local_path
                   and Path(img_spec.local_path).exists())
    img_h = r.BODY_H - 0.4
    gap = 0.3

    if not has_img and sc.annotations:
        # No usable image: full-width text layout instead of an empty frame.
        await r._frame(s, idx, r.M_LEFT, r.BODY_Y, r.CW, img_h)
        await r._annotation_list(s, idx, sc.annotations,
                                 r.M_LEFT + 0.6, r.BODY_Y + 0.2,
                                 r.CW - 1.2, size=r._sz("body") + 2,
                                 height=img_h - 0.4)
    elif has_img and not sc.annotations:
        # No annotations: center the image at 75% width.
        img_w = r.CW * 0.75
        await r._insert_image(s, idx, img_spec,
                              r.M_LEFT + (r.CW - img_w) / 2,
                              r.BODY_Y, img_w, img_h)
    else:
        img_ratio = r.dna.image_area_ratios.get("image_focus", 0.65)
        img_w = r.CW * img_ratio
        await r._insert_image(s, idx, img_spec, r.M_LEFT, r.BODY_Y, img_w, img_h)
        if sc.annotations:
            ann_left = r.M_LEFT + img_w + gap
            ann_w = r.CW - img_w - gap
            await r._frame(s, idx, ann_left, r.BODY_Y, ann_w, img_h)
            await r._annotation_list(s, idx, sc.annotations,
                                     ann_left + 0.2, r.BODY_Y + 0.2,
                                     ann_w - 0.4, height=img_h - 0.4)

    if sc.citation:
        await r._citation(s, idx, sc.citation)

    return idx


async def slide_dual_image(r, s, sc: SlideContent, pres: Presentation) -> int:
    idx = await r._blank(s)
    await r._header_band(s, idx, sc.title)
    await r._key_statement(s, idx, sc.key_statement)

    gap = 0.35
    col_w = (r.CW - gap) / 2

    if sc.left_label:
        await r._rrect(s, idx, r.M_LEFT, r.BODY_Y, col_w, 0.5, r._primary)
        await r._text(s, idx, r.M_LEFT, r.BODY_Y + 0.05, col_w, 0.4,
                      sc.left_label, size=r._sz("body"), bold=True,
                      color=r._text_on_primary, align="center")
    if sc.right_label:
        right_x = r.M_LEFT + col_w + gap
        await r._rrect(s, idx, right_x, r.BODY_Y, col_w, 0.5, r._accent)
        await r._text(s, idx, right_x, r.BODY_Y + 0.05, col_w, 0.4,
                      sc.right_label, size=r._sz("body"), bold=True,
                      color=r._text_on_primary, align="center")

    label_offset = 0.6 if (sc.left_label or sc.right_label) else 0
    img_top = r.BODY_Y + label_offset
    img_h = r.BODY_H - label_offset - 0.4

    left_img = sc.left_image or (sc.images[0] if len(sc.images) > 0 else None)
    right_img = sc.right_image or (sc.images[1] if len(sc.images) > 1 else None)

    await r._insert_image(s, idx, left_img, r.M_LEFT, img_top, col_w, img_h)
    await r._insert_image(s, idx, right_img, r.M_LEFT + col_w + gap, img_top, col_w, img_h)

    if sc.citation:
        await r._citation(s, idx, sc.citation)

    return idx


async def slide_figure_caption(r, s, sc: SlideContent, pres: Presentation) -> int:
    idx = await r._blank(s)
    await r._header_band(s, idx, sc.title)
    await r._key_statement(s, idx, sc.key_statement)

    fig_h = r.BODY_H - 0.3
    gap = 0.3

    img_spec = sc.images[0] if sc.images else None
    has_img = bool(img_spec and img_spec.local_path
                   and Path(img_spec.local_path).exists())

    if not has_img and sc.annotations:
        await r._frame(s, idx, r.M_LEFT, r.BODY_Y, r.CW, fig_h)
        await r._annotation_list(s, idx, sc.annotations,
                                 r.M_LEFT + 0.6, r.BODY_Y + 0.2,
                                 r.CW - 1.2, size=r._sz("body") + 2,
                                 height=fig_h - 0.4)
    else:
        fig_ratio = r.dna.image_area_ratios.get("figure_caption", 0.55)
        fig_w = r.CW * fig_ratio
        await r._insert_image(s, idx, img_spec, r.M_LEFT, r.BODY_Y, fig_w, fig_h)

        text_left = r.M_LEFT + fig_w + gap
        text_w = r.CW - fig_w - gap
        await r._frame(s, idx, text_left, r.BODY_Y, text_w, fig_h)

        if sc.annotations:
            await r._annotation_list(s, idx, sc.annotations,
                                     text_left + 0.2, r.BODY_Y + 0.2,
                                     text_w - 0.4, height=fig_h - 0.4)

    if sc.citation:
        await r._citation(s, idx, sc.citation)

    return idx


async def slide_chart(r, s, sc: SlideContent, pres: Presentation) -> int:
    idx = await r._blank(s)
    await r._header_band(s, idx, sc.title)
    await r._key_statement(s, idx, sc.key_statement)

    has_side = bool(sc.annotations)
    if has_side:
        chart_w = r.CW * 0.65
        text_left = r.M_LEFT + chart_w + 0.3
        text_w = r.CW - chart_w - 0.3
    else:
        chart_w = r.CW

    chart_h = r.BODY_H - 0.3
    await r._frame(s, idx, r.M_LEFT, r.BODY_Y, chart_w, chart_h)

    cd = sc.chart_data
    if cd and charts.needs_matplotlib(cd):
        # Scientific figure → DesignDNA-styled PNG, inserted image-first.
        png_path = Path(r._image_dir()) / f"chart_{sc.index}.png"
        png = charts.render_chart(cd, r.dna, png_path,
                                  width_in=chart_w - 0.2, height_in=chart_h - 0.2)
        if png:
            spec = ImageSpec(description=cd.title or "figure", local_path=png)
            await r._insert_image(s, idx, spec, r.M_LEFT + 0.1,
                                  r.BODY_Y + 0.1, chart_w - 0.2, chart_h - 0.2)
    elif cd and cd.categories:
        series_names = [sr.get("name", f"Series {i+1}") for i, sr in enumerate(cd.series)]
        series_values = [sr.get("values", []) for sr in cd.series]
        await s.call("add_chart", {
            "slide_index": idx,
            "chart_type": cd.chart_type or "column",
            "left": r.M_LEFT + 0.1, "top": r.BODY_Y + 0.1,
            "width": chart_w - 0.2, "height": chart_h - 0.2,
            "categories": cd.categories,
            "series_names": series_names,
            "series_values": series_values,
            "has_legend": True,
            "has_data_labels": cd.chart_type in ("pie", "doughnut"),
            "title": cd.title or "",
            "x_axis_title": cd.x_axis_title or "",
            "y_axis_title": cd.y_axis_title or "",
        })

    if has_side:
        await r._frame(s, idx, text_left, r.BODY_Y, text_w, chart_h)
        await r._annotation_list(s, idx, sc.annotations,
                                 text_left + 0.2, r.BODY_Y + 0.3,
                                 text_w - 0.4, spacing=0.6)

    if sc.citation:
        await r._citation(s, idx, sc.citation)

    return idx


async def slide_process(r, s, sc: SlideContent, pres: Presentation) -> int:
    idx = await r._blank(s)
    await r._header_band(s, idx, sc.title)
    await r._key_statement(s, idx, sc.key_statement)

    steps = sc.process_steps
    if not steps:
        return idx
    n = min(len(steps), 6)
    steps = steps[:n]

    arrow_gap = 0.45
    total_shape_w = r.CW - (n - 1) * arrow_gap
    shape_w = min(total_shape_w / n, 2.5)
    # Compact card sized to content, centered vertically in the body area.
    shape_h = min(r.BODY_H - 0.3, 3.2)
    shape_top = r.BODY_Y + (r.BODY_H - 0.3 - shape_h) / 2
    actual_total = n * shape_w + (n - 1) * arrow_gap
    start_x = r.M_LEFT + (r.CW - actual_total) / 2

    for i, step in enumerate(steps):
        x = start_x + i * (shape_w + arrow_gap)

        await r._frame(s, idx, x, shape_top, shape_w, shape_h)

        await r._rrect(s, idx, x, shape_top, shape_w, 0.55, r._primary)
        await r._text(s, idx, x, shape_top + 0.05, shape_w, 0.45,
                      f"Step {i + 1}", size=r._sz("caption"), bold=True,
                      color=r._text_on_primary, align="center")

        await r._text(s, idx, x + 0.15, shape_top + 0.8,
                      shape_w - 0.3, 1.0,
                      step.label, size=r._sz("body"), bold=True,
                      color=r._text_on_light, align="center")

        if step.description:
            await r._text(s, idx, x + 0.15, shape_top + 1.9,
                          shape_w - 0.3, shape_h - 2.1,
                          step.description, size=r._sz("caption"),
                          bold=False, color=r._text_muted, align="center")

        if i < n - 1:
            ay = shape_top + shape_h / 2
            await s.call("add_shape", {
                "slide_index": idx, "shape_type": "arrow",
                "left": x + shape_w + 0.05, "top": ay - 0.2,
                "width": arrow_gap - 0.1, "height": 0.4,
                "fill_color": r._primary,
                "line_color": r._primary,
            })

    return idx


async def slide_table(r, s, sc: SlideContent, pres: Presentation) -> int:
    idx = await r._blank(s)
    await r._header_band(s, idx, sc.title)
    await r._key_statement(s, idx, sc.key_statement)

    data = sc.table_data
    if not data or len(data) < 2:
        return idx

    rows = len(data)
    cols = max(len(row) for row in data)
    data = [row + [""] * (cols - len(row)) for row in data]

    table_w = min(r.CW, cols * 2.5)
    table_h = min(r.BODY_H - 0.3, rows * 0.55)
    table_left = r.M_LEFT + (r.CW - table_w) / 2
    table_top = r.BODY_Y + (r.BODY_H - 0.3 - table_h) / 2

    await s.call("add_table", {
        "slide_index": idx,
        "rows": rows, "cols": cols,
        "left": table_left, "top": table_top,
        "width": table_w, "height": table_h,
        "data": data,
        "header_row": True,
        "header_font_size": r._sz("caption"),
        "body_font_size": r._sz("citation"),
        "header_bg_color": r._primary,
        "body_bg_color": [255, 255, 255],
        "border_color": lighten(r._primary, 0.5),
    })

    if sc.citation:
        await r._citation(s, idx, sc.citation)

    return idx


async def slide_key_findings(r, s, sc: SlideContent, pres: Presentation) -> int:
    idx = await r._blank(s)
    await r._header_band(s, idx, sc.title)
    await r._key_statement(s, idx, sc.key_statement)

    metrics = sc.metrics
    n = min(len(metrics), 4)
    if n == 0:
        return idx
    metrics = metrics[:n]

    card_gap = 0.3
    card_w = (r.CW - (n - 1) * card_gap) / n
    card_h = min(r.BODY_H - 0.3, 3.4)
    card_top = r.BODY_Y + (r.BODY_H - 0.3 - card_h) / 2

    for i, m in enumerate(metrics):
        x = r.M_LEFT + i * (card_w + card_gap)
        value = m.get("value", "—")
        label = m.get("label", "")
        trend = m.get("trend", "")

        await r._frame(s, idx, x, card_top, card_w, card_h)
        await r._rrect(s, idx, x, card_top, card_w, 0.5, r._primary)

        await r._text(s, idx, x + 0.2, card_top + 0.8, card_w - 0.4, 1.2,
                      str(value), size=r._sz("header"), bold=True,
                      color=r._primary, align="center")

        await r._text(s, idx, x + 0.2, card_top + 2.1, card_w - 0.4, 0.6,
                      label, size=r._sz("body"), bold=True,
                      color=r._text_on_light, align="center")

        if trend:
            await r._text(s, idx, x + 0.2, card_top + 2.7, card_w - 0.4, 0.4,
                          trend, size=r._sz("caption"), bold=True,
                          color=r._primary, align="center")

    return idx


async def slide_text_block(r, s, sc: SlideContent, pres: Presentation) -> int:
    """Clean text slide: header + key statement + framed body of points.

    Optionally pairs a side figure if an image is provided. Used for
    definitions, procedures, and reference text (courseware).
    """
    idx = await r._blank(s)
    await r._header_band(s, idx, sc.title)
    await r._key_statement(s, idx, sc.key_statement)

    items = [a for a in sc.annotations if a.strip()]
    has_fig = bool(sc.images and sc.images[0].local_path)

    if has_fig:
        fig_w = r.CW * 0.42
        fig_h = r.BODY_H - 0.3
        await r._insert_image(s, idx, sc.images[0],
                              r.M_LEFT + r.CW - fig_w, r.BODY_Y, fig_w, fig_h)
        body_left = r.M_LEFT
        body_w = r.CW - fig_w - 0.35
    else:
        body_left = r.M_LEFT
        body_w = r.CW

    if not items:
        return idx

    await r._frame(s, idx, body_left, r.BODY_Y, body_w, r.BODY_H - 0.3)

    n = len(items)
    # Auto-size: more lines -> smaller font, within body/caption range.
    size = r._sz("body")
    if n > 5:
        size = max(r._sz("caption"), int(size * 5 / n))
    inner_top = r.BODY_Y + 0.25
    inner_h = r.BODY_H - 0.3 - 0.5
    line_h = inner_h / n
    y = inner_top
    for item in items:
        await r._text(s, idx, body_left + 0.3, y, body_w - 0.6, line_h,
                      f"•  {item}", size=size, bold=False,
                      color=r._text_on_light)
        y += line_h

    if sc.citation:
        await r._citation(s, idx, sc.citation)
    return idx


async def slide_references(r, s, sc: SlideContent, pres: Presentation) -> int:
    idx = await r._blank(s)
    await r._header_band(s, idx, sc.title)

    refs = sc.references
    if not refs:
        return idx

    refs = refs[:15]
    ref_size = r._sz("citation")
    available = r.CONTENT_BOTTOM - (r.KEY_Y + 0.1)
    # Spread entries across the body when the list is short.
    line_h = max(0.45, min(0.8, available / len(refs)))
    y = r.KEY_Y + 0.1 + max(0.0, (available - line_h * len(refs)) / 2)

    for ref in refs:
        await r._text(s, idx, r.M_LEFT + 0.1, y, r.CW - 0.2, line_h,
                      ref, size=ref_size, bold=False,
                      color=r._text_on_light)
        y += line_h
        if y > r.CONTENT_BOTTOM - 0.3:
            break

    return idx


async def slide_closing(r, s, sc: SlideContent, pres: Presentation) -> int:
    idx = await r._blank(s)

    await r._rect(s, idx, 0, 0, r.W, 0.12, r._primary)

    await r._text(s, idx, 0.8, 2.3, r.W - 1.6, 1.6,
                  sc.title, size=r._sz("big_title"), bold=True,
                  color=r._primary, align="center")

    await r._rect(s, idx, r.W / 2 - 0.9, 4.05, 1.8, 0.05, r._accent)

    if sc.annotations:
        info_text = "\n".join(sc.annotations)
        await r._text(s, idx, 0, 4.4, r.W, 1.6,
                      info_text, size=r._sz("body"),
                      bold=False, color=r._text_muted, align="center")

    await r._rect(s, idx, 0, r.H - 0.85, r.W, 0.85, r._primary)

    return idx


DISPATCH = {
    SlideLayout.TITLE: slide_title,
    SlideLayout.SECTION: slide_section,
    SlideLayout.IMAGE_FOCUS: slide_image_focus,
    SlideLayout.DUAL_IMAGE: slide_dual_image,
    SlideLayout.FIGURE_CAPTION: slide_figure_caption,
    SlideLayout.TEXT_BLOCK: slide_text_block,
    SlideLayout.CHART: slide_chart,
    SlideLayout.PROCESS_FLOW: slide_process,
    SlideLayout.TABLE: slide_table,
    SlideLayout.KEY_FINDINGS: slide_key_findings,
    SlideLayout.REFERENCES: slide_references,
    SlideLayout.CLOSING: slide_closing,
}
