"""Academic-specific utilities: formulas, references, logo/watermark."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def latex_to_image(formula: str, output_path: str = "", dpi: int = 300) -> str | None:
    """Render a LaTeX formula to a PNG image.

    Tries matplotlib first, then falls back to a simple text representation.
    Returns the image path on success, None on failure.
    """
    if not output_path:
        output_path = str(Path(tempfile.gettempdir()) / "ppt_agent_images" / "formula.png")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        return _render_matplotlib(formula, output_path, dpi)
    except Exception:
        pass

    try:
        return _render_latex_cli(formula, output_path, dpi)
    except Exception:
        pass

    return None


def _render_matplotlib(formula: str, output_path: str, dpi: int) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 1.5))
    ax.axis("off")
    ax.text(0.5, 0.5, f"${formula}$", fontsize=28,
            ha="center", va="center", transform=ax.transAxes)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight",
                transparent=True, pad_inches=0.1)
    plt.close(fig)
    return output_path


def _render_latex_cli(formula: str, output_path: str, dpi: int) -> str:
    """Try rendering via command-line LaTeX + dvipng."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = Path(tmpdir) / "formula.tex"
        tex_content = (
            r"\documentclass[preview]{standalone}"
            r"\usepackage{amsmath}"
            r"\begin{document}"
            f"${formula}$"
            r"\end{document}"
        )
        tex_path.write_text(tex_content)

        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, str(tex_path)],
            capture_output=True, timeout=15,
        )

        pdf_path = Path(tmpdir) / "formula.pdf"
        if pdf_path.exists():
            subprocess.run(
                ["convert", "-density", str(dpi), str(pdf_path), output_path],
                capture_output=True, timeout=10,
            )
            if Path(output_path).exists():
                return output_path

    raise RuntimeError("LaTeX CLI rendering failed")


def format_references(refs: list[str | dict]) -> list[str]:
    """Format a list of references into numbered citation strings.

    Accepts either plain strings or dicts with author/year/title/source keys.
    """
    formatted = []
    for i, ref in enumerate(refs, 1):
        if isinstance(ref, str):
            formatted.append(f"[{i}] {ref}")
        elif isinstance(ref, dict):
            author = ref.get("author", "Unknown")
            year = ref.get("year", "")
            title = ref.get("title", "")
            source = ref.get("source", "")
            parts = [author]
            if year:
                parts[0] += f" ({year})"
            if title:
                parts.append(title)
            if source:
                parts.append(source)
            formatted.append(f"[{i}] {'. '.join(parts)}.")
    return formatted


def logo_placement(slide_width: float, slide_height: float,
                   logo_width: float = 0.8, position: str = "bottom-right",
                   margin: float = 0.3) -> dict:
    """Calculate logo position coordinates.

    Returns dict with left, top, width, height for the logo placement.
    """
    aspect_ratio = 1.0  # square by default; caller can override
    logo_height = logo_width / aspect_ratio

    positions = {
        "bottom-right": (slide_width - logo_width - margin, slide_height - logo_height - margin),
        "bottom-left": (margin, slide_height - logo_height - margin),
        "top-right": (slide_width - logo_width - margin, margin),
        "top-left": (margin, margin),
    }
    left, top = positions.get(position, positions["bottom-right"])

    return {
        "left": left,
        "top": top,
        "width": logo_width,
        "height": logo_height,
    }
