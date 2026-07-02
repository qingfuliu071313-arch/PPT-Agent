"""Stage 5: Source images for slides — search, download, validate."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from pathlib import Path

from rich.console import Console

from ppt_agent.models import ImageSpec, SlideContent, SlideLayout
from ppt_agent.utils.image_search import (
    download_image,
    ensure_image_dir,
    get_search_stats,
    reset_search_stats,
    search_image_urls,
)

console = Console()


class ImageSourcer:
    """Search, download, and validate images for presentation slides."""

    # Layouts that require images
    IMAGE_LAYOUTS = {
        SlideLayout.IMAGE_FOCUS,
        SlideLayout.DUAL_IMAGE,
        SlideLayout.FIGURE_CAPTION,
    }

    def __init__(self) -> None:
        self._search_cache: dict[str, list[str]] = {}
        self._query_uses: dict[str, int] = defaultdict(int)

    def source_all(self, slides: list[SlideContent]) -> list[SlideContent]:
        """Download images for all slides. Returns updated slides."""
        ensure_image_dir()
        reset_search_stats()
        self._search_cache = {}
        self._query_uses = defaultdict(int)

        specs = self._collect_specs(slides)
        if not specs:
            return slides

        asyncio.run(self._download_batch(specs))
        self._report_degradation()
        return slides

    def _report_degradation(self) -> None:
        """Surface search/download failures instead of silently placeholding."""
        stats = get_search_stats()
        if stats["search_errors"]:
            console.print(
                f"  [yellow]图片搜索后端失败 {stats['search_errors']} 次"
                f"（网络问题会导致对应页使用占位图）[/yellow]"
            )
        if stats["curl_missing"]:
            console.print("  [yellow]curl 不可用：无法下载图片，全部使用占位图[/yellow]")

    def _collect_specs(self, slides: list[SlideContent]) -> list[ImageSpec]:
        """Collect all ImageSpecs that need downloading."""
        specs = []
        for sc in slides:
            for img in sc.images:
                if img.search_query and not img.local_path:
                    specs.append(img)
            if sc.left_image and sc.left_image.search_query and not sc.left_image.local_path:
                specs.append(sc.left_image)
            if sc.right_image and sc.right_image.search_query and not sc.right_image.local_path:
                specs.append(sc.right_image)
            for step in sc.process_steps:
                if step.icon_search and not step.icon_path:
                    specs.append(ImageSpec(
                        description=step.label,
                        search_query=step.icon_search,
                    ))
        return specs

    async def _download_batch(self, specs: list[ImageSpec]) -> None:
        """Download images in parallel batches."""
        # Prefetch each unique query exactly once (avoids duplicate searches
        # when same-query specs land in the same concurrent batch).
        unique = list({
            s.search_query for s in specs
            if s.search_query and not s.search_query.startswith("http")
        })
        results = await asyncio.gather(*[
            asyncio.to_thread(search_image_urls, q, 6) for q in unique
        ], return_exceptions=True)
        for q, r in zip(unique, results):
            self._search_cache[q] = r if isinstance(r, list) else []

        batch_size = 5
        for i in range(0, len(specs), batch_size):
            batch = specs[i:i + batch_size]
            tasks = [self._download_one(spec) for spec in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _download_one(self, spec: ImageSpec) -> None:
        """Search and download an image for the spec, or create placeholder."""
        if not spec.search_query:
            return

        if spec.search_query.startswith("http"):
            candidates = [spec.search_query]
        else:
            candidates = await self._search_cached(spec.search_query)

        for n, url in enumerate(candidates):
            path = await asyncio.to_thread(download_image, url)
            if path and self._validate_image(path):
                spec.local_path = path
                spec.candidate_urls = candidates[n + 1:]  # keep alternates for QA swaps
                return

        placeholder = self._create_placeholder(spec.description)
        if placeholder:
            spec.local_path = placeholder

    async def _search_cached(self, query: str) -> list[str]:
        """Search each unique query once per run; repeat uses rotate the
        candidate order so slides sharing a query prefer different images."""
        if query not in self._search_cache:
            self._search_cache[query] = await asyncio.to_thread(
                search_image_urls, query, 6
            )
        candidates = self._search_cache[query]
        offset = self._query_uses[query] % len(candidates) if candidates else 0
        self._query_uses[query] += 1
        return candidates[offset:] + candidates[:offset]

    def resource_next(self, spec: ImageSpec) -> bool:
        """Swap the spec's image to the next valid candidate (visual QA fix)."""
        while spec.candidate_urls:
            url = spec.candidate_urls.pop(0)
            path = download_image(url)
            if path and self._validate_image(path):
                spec.local_path = path
                return True
        return False

    def _validate_image(self, path: str) -> bool:
        """Check the file is a real PNG/JPEG image, not an HTML error page."""
        p = Path(path)
        if not p.exists() or p.stat().st_size < 5000:
            return False
        try:
            with open(path, "rb") as f:
                header = f.read(12)
            if header[:4] == b"\x89PNG":
                return True
            if header[:2] == b"\xff\xd8":
                return True
            return False
        except Exception:
            return False

    def _create_placeholder(self, text: str) -> str | None:
        """Create a simple placeholder image with text label."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGB", (800, 600), color=(245, 245, 245))
            draw = ImageDraw.Draw(img)

            draw.rectangle([20, 20, 780, 580], outline=(200, 200, 200), width=2)

            try:
                font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 24)
            except (OSError, IOError):
                font = ImageFont.load_default()

            label = text[:40] + "..." if len(text) > 40 else text
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (800 - tw) // 2
            y = (600 - th) // 2
            draw.text((x, y), label, fill=(150, 150, 150), font=font)

            dest = ensure_image_dir() / f"placeholder_{hash(text) & 0xFFFFFFFF:08x}.png"
            img.save(str(dest))
            return str(dest)
        except ImportError:
            return None
