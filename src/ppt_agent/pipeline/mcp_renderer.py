"""Render presentations via the Office-PowerPoint MCP Server.

DesignDNA-driven renderer: all geometry, colors, and fonts come from
the DesignDNA profile extracted from a reference template.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ppt_agent.models import DesignDNA, Presentation, SlideContent, SlideLayout
from ppt_agent.utils.fonts import font_for_text, get_font_pair


def _hex(color: str) -> list[int]:
    h = color.lstrip("#")
    return [int(h[i : i + 2], 16) for i in (0, 2, 4)]


def _lighten(rgb: list[int], factor: float = 0.3) -> list[int]:
    return [min(255, int(c + (255 - c) * factor)) for c in rgb]


class MCPRenderer:
    """DesignDNA-driven presentation renderer using the MCP Server tool palette."""

    _RATIOS = {
        "16:9": (13.333, 7.5),
        "4:3": (10.0, 7.5),
    }

    SPACING = 0.12
    CARD_PAD = 0.15
    ELEM_GAP = 0.2

    _TRANSITIONS = {
        SlideLayout.TITLE: {"transition_type": "fade", "duration": 1.0},
        SlideLayout.SECTION: {"transition_type": "fade", "duration": 0.8},
        SlideLayout.CLOSING: {"transition_type": "fade", "duration": 1.0},
    }
    _DEFAULT_TRANSITION = {"transition_type": "fade", "duration": 0.5}

    def __init__(self, design_dna: DesignDNA | None = None, aspect_ratio: str = "16:9"):
        self.dna = design_dna or DesignDNA()
        self._server_params = StdioServerParameters(
            command="uvx",
            args=["--from", "office-powerpoint-mcp-server", "ppt_mcp_server"],
        )
        self._pres_id: str = ""
        self._section_num = 0
        self._font_title, self._font_body = get_font_pair()

        dims = self._RATIOS.get(aspect_ratio, self._RATIOS["16:9"])
        self.W, self.H = dims
        self._compute_geometry()

    def _compute_geometry(self) -> None:
        """Derive all layout positions from DesignDNA ratios."""
        dna = self.dna
        self.HDR_TOP = self.H * dna.header_bar.get("top_ratio", 0.033)
        self.HDR_H = self.H * dna.header_bar.get("height_ratio", 0.084)
        self.M_LEFT = self.W * dna.content_margins.get("left", 0.06)
        self.M_RIGHT = self.W * dna.content_margins.get("right", 0.06)
        self.CONTENT_TOP = self.H * dna.content_margins.get("top", 0.16)
        self.CONTENT_BOTTOM = self.H * (1 - dna.content_margins.get("bottom", 0.07))
        self.CW = self.W - self.M_LEFT - self.M_RIGHT
        self.CH = self.CONTENT_BOTTOM - self.CONTENT_TOP
        self.CITE_Y = self.H - 0.55
        self.KEY_Y = self.HDR_TOP + self.HDR_H + 0.12
        self.KEY_H = 0.65
        self.BODY_Y = self.KEY_Y + self.KEY_H + 0.1
        self.BODY_H = self.CONTENT_BOTTOM - self.BODY_Y

    def render(self, presentation: Presentation, output_path: str) -> str:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        asyncio.run(self._render_async(presentation, str(path.resolve())))
        self._apply_slide_size(path)
        return str(path)

    def _apply_slide_size(self, path: Path) -> None:
        """Set the saved deck's page size to match render geometry.

        The MCP server creates 4:3 decks and exposes no sizing tool, while
        all geometry here targets self.W x self.H. Shape positions are
        absolute EMU, so resizing the page after save is lossless.
        """
        from pptx import Presentation as PptxPresentation
        from pptx.util import Inches

        pptx = PptxPresentation(str(path))
        pptx.slide_width = Inches(self.W)
        pptx.slide_height = Inches(self.H)
        pptx.save(str(path))

    # ── async core ─────────────────────────────────────────────

    async def _render_async(self, pres: Presentation, out: str) -> None:
        async with stdio_client(self._server_params) as streams:
            async with ClientSession(*streams) as s:
                await s.initialize()
                await self._build(s, pres, out)

    async def _build(self, s: ClientSession, pres: Presentation, out: str) -> None:
        r = await self._call(s, "create_presentation", {"id": "ppt_agent"})
        self._pres_id = r.get("presentation_id", "ppt_agent")
        self._section_num = 0

        await self._call(s, "set_core_properties", {
            "title": pres.outline.title,
            "author": pres.author or "",
        })

        total = len(pres.slides)
        checkpoint_path = out + ".checkpoint"
        completed = self._load_checkpoint(checkpoint_path)

        for i, sc in enumerate(pres.slides):
            if i < completed:
                continue

            try:
                idx = await self._dispatch(s, sc, pres, i)
                if sc.layout not in (SlideLayout.TITLE, SlideLayout.CLOSING, SlideLayout.SECTION):
                    await self._footer(s, idx, i + 1, total)
                self._save_checkpoint(checkpoint_path, i + 1)
            except Exception as e:
                self._save_checkpoint(checkpoint_path, i)
                await self._call(s, "save_presentation", {"file_path": out})
                raise RuntimeError(
                    f"Render failed at slide {i + 1}/{total} ({sc.layout.value}): {e}. "
                    f"Partial result saved. Re-run to resume from slide {i + 1}."
                ) from e

        await self._call(s, "save_presentation", {"file_path": out})
        self._clear_checkpoint(checkpoint_path)

    @staticmethod
    def _load_checkpoint(path: str) -> int:
        try:
            with open(path) as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return 0

    @staticmethod
    def _save_checkpoint(path: str, slide_num: int) -> None:
        with open(path, "w") as f:
            f.write(str(slide_num))

    @staticmethod
    def _clear_checkpoint(path: str) -> None:
        try:
            Path(path).unlink()
        except FileNotFoundError:
            pass

    async def _call(self, s: ClientSession, tool: str, args: dict) -> dict:
        if self._pres_id and "presentation_id" not in args:
            args = {**args, "presentation_id": self._pres_id}
        result = await s.call_tool(tool, arguments=args)
        if result.content:
            for block in result.content:
                if hasattr(block, "text"):
                    try:
                        return json.loads(block.text)
                    except (json.JSONDecodeError, AttributeError):
                        return {"raw": block.text}
        return {}

    async def _dispatch(self, s: ClientSession, sc: SlideContent, pres: Presentation, i: int) -> int:
        dispatch = {
            SlideLayout.TITLE: self._slide_title,
            SlideLayout.SECTION: self._slide_section,
            SlideLayout.IMAGE_FOCUS: self._slide_image_focus,
            SlideLayout.DUAL_IMAGE: self._slide_dual_image,
            SlideLayout.FIGURE_CAPTION: self._slide_figure_caption,
            SlideLayout.TEXT_BLOCK: self._slide_text_block,
            SlideLayout.CHART: self._slide_chart,
            SlideLayout.PROCESS_FLOW: self._slide_process,
            SlideLayout.TABLE: self._slide_table,
            SlideLayout.KEY_FINDINGS: self._slide_key_findings,
            SlideLayout.REFERENCES: self._slide_references,
            SlideLayout.CLOSING: self._slide_closing,
        }
        fn = dispatch.get(sc.layout, self._slide_image_focus)
        idx = await fn(s, sc, pres)

        trans = self._TRANSITIONS.get(sc.layout, self._DEFAULT_TRANSITION)
        try:
            await self._call(s, "manage_slide_transitions", {"slide_index": idx, **trans})
        except Exception:
            pass

        if sc.notes:
            try:
                await self._call(s, "manage_text", {
                    "slide_index": idx, "operation": "add",
                    "target": "notes", "text": sc.notes,
                })
            except Exception:
                pass

        return idx

    # ── DNA color helpers ─────────────────────────────────────

    @property
    def _primary(self) -> list[int]:
        return _hex(self.dna.primary_color)

    @property
    def _accent(self) -> list[int]:
        return _hex(self.dna.accent_color)

    @property
    def _bg2(self) -> list[int]:
        return _hex(self.dna.secondary_color)

    @property
    def _text_on_primary(self) -> list[int]:
        return _hex(self.dna.text_on_primary)

    @property
    def _text_on_light(self) -> list[int]:
        return _hex(self.dna.text_on_light)

    @property
    def _text_muted(self) -> list[int]:
        return _hex(self.dna.text_muted)

    @property
    def _frame_color(self) -> list[int]:
        return _hex(self.dna.frame_border_color)

    def _sz(self, tier: str) -> int:
        return self.dna.size_hierarchy.get(tier, 20)

    # ── visual primitives ──────────────────────────────────────

    async def _blank(self, s: ClientSession) -> int:
        r = await self._call(s, "add_slide", {"layout_index": 6})
        return r.get("slide_index", 0)

    async def _rect(self, s, idx, left, top, w, h, fill, **kw) -> dict:
        kw.setdefault("line_color", fill)
        args = {
            "slide_index": idx, "shape_type": "rectangle",
            "left": left, "top": top, "width": w, "height": h,
            "fill_color": fill,
        }
        args.update(kw)
        return await self._call(s, "add_shape", args)

    async def _rrect(self, s, idx, left, top, w, h, fill, **kw) -> dict:
        kw.setdefault("line_color", fill)
        args = {
            "slide_index": idx, "shape_type": "rounded_rectangle",
            "left": left, "top": top, "width": w, "height": h,
            "fill_color": fill,
        }
        args.update(kw)
        return await self._call(s, "add_shape", args)

    async def _circle(self, s, idx, left, top, size, fill, **kw) -> dict:
        kw.setdefault("line_color", fill)
        args = {
            "slide_index": idx, "shape_type": "oval",
            "left": left, "top": top, "width": size, "height": size,
            "fill_color": fill,
        }
        args.update(kw)
        return await self._call(s, "add_shape", args)

    async def _text(self, s, idx, left, top, w, h, text, size=18, color=None,
                    bold=False, align="left", font=None) -> dict:
        color = color or self._text_on_light
        if font is None:
            font = font_for_text(text)
        size = self._fit_font_size(text, w, h, size)
        return await self._call(s, "manage_text", {
            "slide_index": idx, "operation": "add",
            "left": left, "top": top, "width": w, "height": h,
            "text": text, "font_size": size, "bold": bold,
            "font_name": font, "color": color, "alignment": align,
        })

    @staticmethod
    def _fit_font_size(text: str, width: float, height: float, base_size: int) -> int:
        cjk = sum(1 for c in text if ord(c) > 0x2E80)
        latin = len(text) - cjk
        char_width = cjk * 1.0 + latin * 0.55
        chars_per_line = max(1, width * 72 / base_size)
        lines_needed = max(1, char_width / chars_per_line)
        line_height = base_size * 1.5 / 72
        total_height = lines_needed * line_height

        size = base_size
        while total_height > height * 1.1 and size > 10:
            size -= 1
            chars_per_line = max(1, width * 72 / size)
            lines_needed = max(1, char_width / chars_per_line)
            line_height = size * 1.5 / 72
            total_height = lines_needed * line_height

        return size

    async def _shadow(self, s, idx, shape_idx) -> None:
        try:
            await self._call(s, "apply_picture_effects", {
                "slide_index": idx, "shape_index": shape_idx,
                "effects": {
                    "shadow": {
                        "shadow_type": "outer", "blur_radius": 6.0,
                        "distance": 3.0, "direction": 315.0,
                        "color": [0, 0, 0], "transparency": 0.7,
                    }
                },
            })
        except Exception:
            pass

    async def _connector(self, s, idx, x1, y1, x2, y2,
                         color=None, width=1.5, ctype="straight") -> dict:
        color = color or self._accent
        return await self._call(s, "add_connector", {
            "slide_index": idx, "connector_type": ctype,
            "start_x": x1, "start_y": y1, "end_x": x2, "end_y": y2,
            "line_width": width, "color": color,
        })

    # ── composite primitives ───────────────────────────────────

    async def _header_band(self, s, idx, title) -> None:
        size = self._sz("header")
        await self._rect(s, idx, 0, self.HDR_TOP, self.W, self.HDR_H, self._primary)
        await self._text(s, idx, self.M_LEFT, self.HDR_TOP + 0.08,
                         self.CW, self.HDR_H - 0.16,
                         title, size=size, bold=True,
                         color=self._text_on_primary, align="center")

    async def _key_statement(self, s, idx, text) -> None:
        if not text:
            return
        size = self._sz("key_statement")
        await self._text(s, idx, 0, self.KEY_Y, self.W, self.KEY_H,
                         text, size=size, bold=True,
                         color=self._text_on_light, align="center")

    async def _frame(self, s, idx, left, top, w, h, line_color=None) -> dict:
        lc = line_color or self._frame_color
        return await self._rrect(s, idx, left, top, w, h, [255, 255, 255],
                                 line_color=lc, line_width=self.dna.frame_border_width)

    async def _annotation_list(self, s, idx, items, left, top, w,
                               size=None, spacing=None, height=None) -> float:
        """Render a bullet list; with `height`, distribute and center vertically."""
        size = size or self._sz("body")
        items = items[:5]
        n = max(len(items), 1)
        if height:
            sp = spacing or min(1.0, height / n)
            y = top + max(0.0, (height - n * sp) / 2)
        else:
            sp = spacing or min(0.7, self.BODY_H / n)
            y = top
        for item in items:
            await self._text(s, idx, left, y, w, min(0.9, sp),
                             f"•  {item}", size=size, bold=False,
                             color=self._text_on_light)
            y += sp
        return y

    async def _citation(self, s, idx, text) -> None:
        if not text:
            return
        await self._text(s, idx, self.M_LEFT, self.CITE_Y, self.CW, 0.35,
                         text, size=self._sz("citation"), bold=False,
                         color=self._text_muted)

    async def _footer(self, s, idx, page, total) -> None:
        await self._text(s, idx, self.W - 1.4, self.H - 0.35, 1.0, 0.25,
                         f"{page} / {total}", size=10, bold=False,
                         color=self._text_muted, align="right")

    @staticmethod
    def _aspect_fit(image_path: str, left: float, top: float,
                    w: float, h: float) -> tuple[float, float, float, float]:
        """Fit the image inside the box preserving aspect ratio, centered."""
        try:
            from PIL import Image

            with Image.open(image_path) as im:
                iw, ih = im.size
            scale = min(w / iw, h / ih)
            fw, fh = iw * scale, ih * scale
            return left + (w - fw) / 2, top + (h - fh) / 2, fw, fh
        except Exception:
            return left, top, w, h

    async def _insert_image(self, s, idx, img_spec, left, top, w, h) -> None:
        """Insert an image file or a placeholder frame."""
        if img_spec and img_spec.local_path and Path(img_spec.local_path).exists():
            try:
                fl, ft, fw, fh = self._aspect_fit(img_spec.local_path, left, top, w, h)
                r = await self._call(s, "manage_image", {
                    "slide_index": idx, "operation": "add",
                    "image_source": img_spec.local_path, "source_type": "file",
                    "left": fl, "top": ft, "width": fw, "height": fh,
                })
                if "error" in r:
                    raise RuntimeError(r["error"])
                if img_spec.caption:
                    await self._text(s, idx, left, top + h + 0.05, w, 0.35,
                                     img_spec.caption, size=self._sz("caption"),
                                     bold=False, color=self._text_muted, align="center")
                return
            except Exception:
                pass

        await self._frame(s, idx, left, top, w, h)
        desc = img_spec.description if img_spec else "Image"
        await self._text(s, idx, left + 0.3, top + h / 2 - 0.3, w - 0.6, 0.6,
                         f"[ {desc} ]", size=self._sz("caption"), bold=True,
                         color=self._text_muted, align="center")

    # ══════════════════════════════════════════════════════════
    #  SLIDE TYPES
    # ══════════════════════════════════════════════════════════

    async def _slide_title(self, s, sc: SlideContent, pres: Presentation) -> int:
        idx = await self._blank(s)

        await self._rect(s, idx, 0, 0, self.W, 0.12, self._primary)

        if sc.annotations:
            await self._text(s, idx, 0, 1.15, self.W, 0.5,
                             sc.annotations[0], size=self._sz("caption") + 2,
                             bold=False, color=self._text_muted, align="center")

        await self._text(s, idx, 0.8, 2.1, self.W - 1.6, 1.9,
                         sc.title, size=self._sz("big_title"), bold=True,
                         color=self._primary, align="center")

        await self._rect(s, idx, self.W / 2 - 0.9, 4.25, 1.8, 0.05, self._accent)

        meta_parts = []
        if pres.author:
            meta_parts.append(pres.author)
        if pres.date:
            meta_parts.append(pres.date)
        if meta_parts:
            await self._text(s, idx, 0, 4.6, self.W, 1.4,
                             "\n".join(meta_parts), size=self._sz("body"),
                             bold=False, color=self._text_muted, align="center")

        await self._rect(s, idx, 0, self.H - 0.85, self.W, 0.85, self._primary)

        return idx

    # ── Section Page ───────────────────────────────────────────

    async def _slide_section(self, s, sc: SlideContent, pres: Presentation) -> int:
        idx = await self._blank(s)
        self._section_num += 1

        await self._rect(s, idx, 0, 0, 0.25, self.H, self._primary)

        await self._text(s, idx, 0.9, 1.0, 2.8, 1.7,
                         f"{self._section_num:02d}", size=80, bold=True,
                         color=self._primary)

        await self._text(s, idx, 3.2, 1.35, self.W - 4.2, 1.3,
                         sc.title, size=self._sz("big_title") - 8, bold=True,
                         color=self._text_on_light)

        if sc.annotations:
            await self._text(s, idx, 3.2, 2.5, self.W - 4.2, 0.5,
                             sc.annotations[0], size=self._sz("caption") + 2,
                             bold=False, color=self._text_muted)

        await self._rect(s, idx, 0.9, 3.15, self.W - 2.0, 0.025,
                         _lighten(self._primary, 0.6))

        # Agenda: current section highlighted, others muted.
        sections = []
        sec_num = 0
        for so in (pres.outline.slides if pres.outline else []):
            if so.layout == SlideLayout.SECTION:
                sec_num += 1
                sections.append((sec_num, so.title))
        y = 3.6
        for num, title in sections[:6]:
            current = num == self._section_num
            marker = "▸ " if current else ""
            await self._text(s, idx, 1.2, y, self.W - 2.6, 0.5,
                             f"{marker}{num:02d}  {title}",
                             size=self._sz("body") + (2 if current else 0),
                             bold=current,
                             color=self._primary if current else self._text_muted)
            y += 0.58

        return idx

    # ── Image Focus Page (★ core layout) ──────────────────────

    async def _slide_image_focus(self, s, sc: SlideContent, pres: Presentation) -> int:
        idx = await self._blank(s)
        await self._header_band(s, idx, sc.title)
        await self._key_statement(s, idx, sc.key_statement)

        img_spec = sc.images[0] if sc.images else None
        has_img = bool(img_spec and img_spec.local_path
                       and Path(img_spec.local_path).exists())
        img_h = self.BODY_H - 0.4
        gap = 0.3

        if not has_img and sc.annotations:
            # No usable image: full-width text layout instead of an empty frame.
            await self._frame(s, idx, self.M_LEFT, self.BODY_Y, self.CW, img_h)
            await self._annotation_list(s, idx, sc.annotations,
                                        self.M_LEFT + 0.6, self.BODY_Y + 0.2,
                                        self.CW - 1.2, size=self._sz("body") + 2,
                                        height=img_h - 0.4)
        elif has_img and not sc.annotations:
            # No annotations: center the image at 75% width.
            img_w = self.CW * 0.75
            await self._insert_image(s, idx, img_spec,
                                     self.M_LEFT + (self.CW - img_w) / 2,
                                     self.BODY_Y, img_w, img_h)
        else:
            img_ratio = self.dna.image_area_ratios.get("image_focus", 0.65)
            img_w = self.CW * img_ratio
            await self._insert_image(s, idx, img_spec, self.M_LEFT, self.BODY_Y, img_w, img_h)
            if sc.annotations:
                ann_left = self.M_LEFT + img_w + gap
                ann_w = self.CW - img_w - gap
                await self._frame(s, idx, ann_left, self.BODY_Y, ann_w, img_h)
                await self._annotation_list(s, idx, sc.annotations,
                                            ann_left + 0.2, self.BODY_Y + 0.2,
                                            ann_w - 0.4, height=img_h - 0.4)

        if sc.citation:
            await self._citation(s, idx, sc.citation)

        return idx

    # ── Dual Image Page ───────────────────────────────────────

    async def _slide_dual_image(self, s, sc: SlideContent, pres: Presentation) -> int:
        idx = await self._blank(s)
        await self._header_band(s, idx, sc.title)
        await self._key_statement(s, idx, sc.key_statement)

        gap = 0.35
        col_w = (self.CW - gap) / 2
        img_h = self.BODY_H - 1.0

        if sc.left_label:
            await self._rrect(s, idx, self.M_LEFT, self.BODY_Y, col_w, 0.5, self._primary)
            await self._text(s, idx, self.M_LEFT, self.BODY_Y + 0.05, col_w, 0.4,
                             sc.left_label, size=self._sz("body"), bold=True,
                             color=self._text_on_primary, align="center")
        if sc.right_label:
            right_x = self.M_LEFT + col_w + gap
            await self._rrect(s, idx, right_x, self.BODY_Y, col_w, 0.5, self._accent)
            await self._text(s, idx, right_x, self.BODY_Y + 0.05, col_w, 0.4,
                             sc.right_label, size=self._sz("body"), bold=True,
                             color=self._text_on_primary, align="center")

        label_offset = 0.6 if (sc.left_label or sc.right_label) else 0
        img_top = self.BODY_Y + label_offset
        img_h = self.BODY_H - label_offset - 0.4

        left_img = sc.left_image or (sc.images[0] if len(sc.images) > 0 else None)
        right_img = sc.right_image or (sc.images[1] if len(sc.images) > 1 else None)

        await self._insert_image(s, idx, left_img, self.M_LEFT, img_top, col_w, img_h)
        await self._insert_image(s, idx, right_img, self.M_LEFT + col_w + gap, img_top, col_w, img_h)

        if sc.citation:
            await self._citation(s, idx, sc.citation)

        return idx

    # ── Figure + Caption Page ─────────────────────────────────

    async def _slide_figure_caption(self, s, sc: SlideContent, pres: Presentation) -> int:
        idx = await self._blank(s)
        await self._header_band(s, idx, sc.title)
        await self._key_statement(s, idx, sc.key_statement)

        fig_h = self.BODY_H - 0.3
        gap = 0.3

        img_spec = sc.images[0] if sc.images else None
        has_img = bool(img_spec and img_spec.local_path
                       and Path(img_spec.local_path).exists())

        if not has_img and sc.annotations:
            await self._frame(s, idx, self.M_LEFT, self.BODY_Y, self.CW, fig_h)
            await self._annotation_list(s, idx, sc.annotations,
                                        self.M_LEFT + 0.6, self.BODY_Y + 0.2,
                                        self.CW - 1.2, size=self._sz("body") + 2,
                                        height=fig_h - 0.4)
        else:
            fig_ratio = self.dna.image_area_ratios.get("figure_caption", 0.55)
            fig_w = self.CW * fig_ratio
            await self._insert_image(s, idx, img_spec, self.M_LEFT, self.BODY_Y, fig_w, fig_h)

            text_left = self.M_LEFT + fig_w + gap
            text_w = self.CW - fig_w - gap
            await self._frame(s, idx, text_left, self.BODY_Y, text_w, fig_h)

            if sc.annotations:
                await self._annotation_list(s, idx, sc.annotations,
                                            text_left + 0.2, self.BODY_Y + 0.2,
                                            text_w - 0.4, height=fig_h - 0.4)

        if sc.citation:
            await self._citation(s, idx, sc.citation)

        return idx

    # ── Chart Page ─────────────────────────────────────────────

    async def _slide_chart(self, s, sc: SlideContent, pres: Presentation) -> int:
        idx = await self._blank(s)
        await self._header_band(s, idx, sc.title)
        await self._key_statement(s, idx, sc.key_statement)

        has_side = bool(sc.annotations)
        if has_side:
            chart_w = self.CW * 0.65
            text_left = self.M_LEFT + chart_w + 0.3
            text_w = self.CW - chart_w - 0.3
        else:
            chart_w = self.CW

        chart_h = self.BODY_H - 0.3
        await self._frame(s, idx, self.M_LEFT, self.BODY_Y, chart_w, chart_h)

        if sc.chart_data and sc.chart_data.categories:
            cd = sc.chart_data
            series_names = [sr.get("name", f"Series {i+1}") for i, sr in enumerate(cd.series)]
            series_values = [sr.get("values", []) for sr in cd.series]
            await self._call(s, "add_chart", {
                "slide_index": idx,
                "chart_type": cd.chart_type or "column",
                "left": self.M_LEFT + 0.1, "top": self.BODY_Y + 0.1,
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
            await self._frame(s, idx, text_left, self.BODY_Y, text_w, chart_h)
            await self._annotation_list(s, idx, sc.annotations,
                                        text_left + 0.2, self.BODY_Y + 0.3,
                                        text_w - 0.4, spacing=0.6)

        if sc.citation:
            await self._citation(s, idx, sc.citation)

        return idx

    # ── Process / Flow Page ────────────────────────────────────

    async def _slide_process(self, s, sc: SlideContent, pres: Presentation) -> int:
        idx = await self._blank(s)
        await self._header_band(s, idx, sc.title)
        await self._key_statement(s, idx, sc.key_statement)

        steps = sc.process_steps
        if not steps:
            return idx
        n = min(len(steps), 6)
        steps = steps[:n]

        arrow_gap = 0.45
        total_shape_w = self.CW - (n - 1) * arrow_gap
        shape_w = min(total_shape_w / n, 2.5)
        # Compact card sized to content, centered vertically in the body area.
        shape_h = min(self.BODY_H - 0.3, 3.2)
        shape_top = self.BODY_Y + (self.BODY_H - 0.3 - shape_h) / 2
        actual_total = n * shape_w + (n - 1) * arrow_gap
        start_x = self.M_LEFT + (self.CW - actual_total) / 2

        for i, step in enumerate(steps):
            x = start_x + i * (shape_w + arrow_gap)

            await self._frame(s, idx, x, shape_top, shape_w, shape_h)

            await self._rrect(s, idx, x, shape_top, shape_w, 0.55, self._primary)
            await self._text(s, idx, x, shape_top + 0.05, shape_w, 0.45,
                             f"Step {i + 1}", size=self._sz("caption"), bold=True,
                             color=self._text_on_primary, align="center")

            await self._text(s, idx, x + 0.15, shape_top + 0.8,
                             shape_w - 0.3, 1.0,
                             step.label, size=self._sz("body"), bold=True,
                             color=self._text_on_light, align="center")

            if step.description:
                await self._text(s, idx, x + 0.15, shape_top + 1.9,
                                 shape_w - 0.3, shape_h - 2.1,
                                 step.description, size=self._sz("caption"),
                                 bold=False, color=self._text_muted, align="center")

            if i < n - 1:
                ay = shape_top + shape_h / 2
                await self._call(s, "add_shape", {
                    "slide_index": idx, "shape_type": "arrow",
                    "left": x + shape_w + 0.05, "top": ay - 0.2,
                    "width": arrow_gap - 0.1, "height": 0.4,
                    "fill_color": self._primary,
                    "line_color": self._primary,
                })

        return idx

    # ── Table Page ─────────────────────────────────────────────

    async def _slide_table(self, s, sc: SlideContent, pres: Presentation) -> int:
        idx = await self._blank(s)
        await self._header_band(s, idx, sc.title)
        await self._key_statement(s, idx, sc.key_statement)

        data = sc.table_data
        if not data or len(data) < 2:
            return idx

        rows = len(data)
        cols = max(len(row) for row in data)
        data = [row + [""] * (cols - len(row)) for row in data]

        table_w = min(self.CW, cols * 2.5)
        table_h = min(self.BODY_H - 0.3, rows * 0.55)
        table_left = self.M_LEFT + (self.CW - table_w) / 2
        table_top = self.BODY_Y + (self.BODY_H - 0.3 - table_h) / 2

        await self._call(s, "add_table", {
            "slide_index": idx,
            "rows": rows, "cols": cols,
            "left": table_left, "top": table_top,
            "width": table_w, "height": table_h,
            "data": data,
            "header_row": True,
            "header_font_size": self._sz("caption"),
            "body_font_size": self._sz("citation"),
            "header_bg_color": self._primary,
            "body_bg_color": [255, 255, 255],
            "border_color": _lighten(self._primary, 0.5),
        })

        if sc.citation:
            await self._citation(s, idx, sc.citation)

        return idx

    # ── Key Findings Page ──────────────────────────────────────

    async def _slide_key_findings(self, s, sc: SlideContent, pres: Presentation) -> int:
        idx = await self._blank(s)
        await self._header_band(s, idx, sc.title)
        await self._key_statement(s, idx, sc.key_statement)

        metrics = sc.metrics
        n = min(len(metrics), 4)
        if n == 0:
            return idx
        metrics = metrics[:n]

        card_gap = 0.3
        card_w = (self.CW - (n - 1) * card_gap) / n
        card_h = min(self.BODY_H - 0.3, 3.4)
        card_top = self.BODY_Y + (self.BODY_H - 0.3 - card_h) / 2

        for i, m in enumerate(metrics):
            x = self.M_LEFT + i * (card_w + card_gap)
            value = m.get("value", "—")
            label = m.get("label", "")
            trend = m.get("trend", "")

            await self._frame(s, idx, x, card_top, card_w, card_h)
            await self._rrect(s, idx, x, card_top, card_w, 0.5, self._primary)

            await self._text(s, idx, x + 0.2, card_top + 0.8, card_w - 0.4, 1.2,
                             str(value), size=self._sz("header"), bold=True,
                             color=self._primary, align="center")

            await self._text(s, idx, x + 0.2, card_top + 2.1, card_w - 0.4, 0.6,
                             label, size=self._sz("body"), bold=True,
                             color=self._text_on_light, align="center")

            if trend:
                await self._text(s, idx, x + 0.2, card_top + 2.7, card_w - 0.4, 0.4,
                                 trend, size=self._sz("caption"), bold=True,
                                 color=self._primary, align="center")

        return idx

    # ── References Page ────────────────────────────────────────

    async def _slide_text_block(self, s, sc: SlideContent, pres: Presentation) -> int:
        """Clean text slide: header + key statement + framed body of points.

        Optionally pairs a side figure if an image is provided. Used for
        definitions, procedures, and reference text (courseware).
        """
        idx = await self._blank(s)
        await self._header_band(s, idx, sc.title)
        await self._key_statement(s, idx, sc.key_statement)

        items = [a for a in sc.annotations if a.strip()]
        has_fig = bool(sc.images and sc.images[0].local_path)

        if has_fig:
            fig_w = self.CW * 0.42
            fig_h = self.BODY_H - 0.3
            await self._insert_image(s, idx, sc.images[0],
                                     self.M_LEFT + self.CW - fig_w, self.BODY_Y, fig_w, fig_h)
            body_left = self.M_LEFT
            body_w = self.CW - fig_w - 0.35
        else:
            body_left = self.M_LEFT
            body_w = self.CW

        if not items:
            return idx

        await self._frame(s, idx, body_left, self.BODY_Y, body_w, self.BODY_H - 0.3)

        n = len(items)
        # Auto-size: more lines -> smaller font, within body/caption range.
        size = self._sz("body")
        if n > 5:
            size = max(self._sz("caption"), int(size * 5 / n))
        inner_top = self.BODY_Y + 0.25
        inner_h = self.BODY_H - 0.3 - 0.5
        line_h = inner_h / n
        y = inner_top
        for item in items:
            await self._text(s, idx, body_left + 0.3, y, body_w - 0.6, line_h,
                             f"•  {item}", size=size, bold=False,
                             color=self._text_on_light)
            y += line_h

        if sc.citation:
            await self._citation(s, idx, sc.citation)
        return idx

    async def _slide_references(self, s, sc: SlideContent, pres: Presentation) -> int:
        idx = await self._blank(s)
        await self._header_band(s, idx, sc.title)

        refs = sc.references
        if not refs:
            return idx

        refs = refs[:15]
        ref_size = self._sz("citation")
        available = self.CONTENT_BOTTOM - (self.KEY_Y + 0.1)
        # Spread entries across the body when the list is short.
        line_h = max(0.45, min(0.8, available / len(refs)))
        y = self.KEY_Y + 0.1 + max(0.0, (available - line_h * len(refs)) / 2)

        for ref in refs:
            await self._text(s, idx, self.M_LEFT + 0.1, y, self.CW - 0.2, line_h,
                             ref, size=ref_size, bold=False,
                             color=self._text_on_light)
            y += line_h
            if y > self.CONTENT_BOTTOM - 0.3:
                break

        return idx

    # ── Closing Page ───────────────────────────────────────────

    async def _slide_closing(self, s, sc: SlideContent, pres: Presentation) -> int:
        idx = await self._blank(s)

        await self._rect(s, idx, 0, 0, self.W, 0.12, self._primary)

        await self._text(s, idx, 0.8, 2.3, self.W - 1.6, 1.6,
                         sc.title, size=self._sz("big_title"), bold=True,
                         color=self._primary, align="center")

        await self._rect(s, idx, self.W / 2 - 0.9, 4.05, 1.8, 0.05, self._accent)

        if sc.annotations:
            info_text = "\n".join(sc.annotations)
            await self._text(s, idx, 0, 4.4, self.W, 1.6,
                             info_text, size=self._sz("body"),
                             bold=False, color=self._text_muted, align="center")

        await self._rect(s, idx, 0, self.H - 0.85, self.W, 0.85, self._primary)

        return idx
