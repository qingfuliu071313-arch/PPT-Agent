"""Image search and download utility for PPT slides.

Search backends (keyless): Wikimedia Commons first (strong for academic
and scientific imagery), then Openverse. In Opus direct mode, Claude may
still inject URLs directly via search_query; both paths converge on
download_image().
"""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path

import httpx

_IMAGE_DIR = Path(tempfile.gettempdir()) / "ppt_agent_images"

_UA = "PPT-Agent/0.1 (academic presentation generator; contact: local)"
_MIN_WIDTH = 500
_OK_EXTENSIONS = (".png", ".jpg", ".jpeg")


# Generic words that hurt Wikimedia full-text recall when present in a query.
_FILLER_WORDS = {
    "diagram", "image", "photo", "picture", "typical", "example", "illustration",
    "schematic", "figure", "of", "the", "a", "an", "and", "with", "for", "in",
}


def _query_variants(query: str) -> list[str]:
    """Progressively broaden a verbose query so search recall stays usable.

    Wikimedia full-text search returns nothing for 5+ word phrases, while the
    content generator emits descriptive english queries. Try the full query,
    then a filler-stripped version, then the shortest salient prefixes.
    """
    words = query.split()
    variants = [query]

    core = [w for w in words if w.lower() not in _FILLER_WORDS]
    if core and core != words:
        variants.append(" ".join(core))

    base = core or words
    for n in (3, 2):
        if len(base) > n:
            variants.append(" ".join(base[:n]))

    seen: set[str] = set()
    ordered: list[str] = []
    for v in variants:
        if v and v not in seen:
            seen.add(v)
            ordered.append(v)
    return ordered


def search_image_urls(query: str, count: int = 6) -> list[str]:
    """Search free image sources for a keyword, return candidate URLs.

    Falls back to progressively broader query variants until enough
    candidates are found, so verbose descriptive queries still resolve.
    """
    urls: list[str] = []
    for variant in _query_variants(query):
        for backend in (_search_wikimedia, _search_openverse):
            if len(urls) >= count:
                break
            try:
                urls.extend(u for u in backend(variant, count - len(urls)) if u not in urls)
            except Exception:
                continue
        if len(urls) >= count:
            break
    return urls[:count]


def _search_wikimedia(query: str, count: int) -> list[str]:
    resp = httpx.get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": 6,
            "gsrlimit": count * 2,
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "iiurlwidth": 1280,
            "format": "json",
        },
        headers={"User-Agent": _UA},
        timeout=12,
    )
    resp.raise_for_status()
    pages = resp.json().get("query", {}).get("pages", {})
    results = []
    for page in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        for info in page.get("imageinfo", []):
            if info.get("mime") not in ("image/jpeg", "image/png"):
                continue
            if info.get("width", 0) < _MIN_WIDTH:
                continue
            results.append(info.get("thumburl") or info.get("url"))
    return [u for u in results if u][:count]


def _search_openverse(query: str, count: int) -> list[str]:
    resp = httpx.get(
        "https://api.openverse.org/v1/images/",
        params={"q": query, "page_size": count * 2},
        headers={"User-Agent": _UA},
        timeout=12,
    )
    resp.raise_for_status()
    results = []
    for item in resp.json().get("results", []):
        url = item.get("url", "")
        if item.get("width") and item["width"] < _MIN_WIDTH:
            continue
        if url and url.lower().split("?")[0].endswith(_OK_EXTENSIONS):
            results.append(url)
    return results[:count]


def ensure_image_dir() -> Path:
    _IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    return _IMAGE_DIR


def download_image(url: str, filename: str = "") -> str | None:
    """Download an image from URL to temp directory.

    Returns local file path on success, None on failure.
    """
    ensure_image_dir()

    if not filename:
        ext = _guess_extension(url)
        name_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        filename = f"{name_hash}{ext}"

    dest = _IMAGE_DIR / filename

    if dest.exists() and dest.stat().st_size > 0:
        return str(dest)

    try:
        result = subprocess.run(
            ["curl", "-sL", "-o", str(dest), "--max-time", "15", url],
            capture_output=True, timeout=20,
        )
        if result.returncode == 0 and dest.exists() and dest.stat().st_size > 1000:
            return str(dest)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    if dest.exists():
        dest.unlink()
    return None


def _guess_extension(url: str) -> str:
    lower = url.lower().split("?")[0]
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"):
        if lower.endswith(ext):
            return ext
    return ".jpg"


def cleanup_images() -> None:
    """Remove all downloaded temp images."""
    if _IMAGE_DIR.exists():
        for f in _IMAGE_DIR.iterdir():
            try:
                f.unlink()
            except OSError:
                pass
