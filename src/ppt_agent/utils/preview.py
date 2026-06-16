"""Render PPTX files to per-slide PNG previews.

Pipeline: soffice (LibreOffice) converts PPTX -> PDF, PyMuPDF rasterizes
PDF pages -> PNG. Used by the visual QA stage and the GUI.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

_SOFFICE_CANDIDATES = (
    "soffice",
    "/opt/homebrew/bin/soffice",
    "/usr/local/bin/soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
)


def find_soffice() -> str | None:
    for cand in _SOFFICE_CANDIDATES:
        path = shutil.which(cand) or (cand if Path(cand).exists() else None)
        if path:
            return path
    return None


def pptx_to_pdf(pptx_path: str | Path, out_dir: str | Path | None = None) -> Path:
    """Convert a PPTX to PDF via LibreOffice. Returns the PDF path."""
    pptx = Path(pptx_path).resolve()
    if not pptx.exists():
        raise FileNotFoundError(pptx)
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError(
            "LibreOffice (soffice) not found. Install it to enable previews: "
            "brew install --cask libreoffice"
        )
    out = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="ppt_preview_"))
    out.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf",
         "--outdir", str(out), str(pptx)],
        capture_output=True, timeout=180,
    )
    pdf = out / (pptx.stem + ".pdf")
    if result.returncode != 0 or not pdf.exists():
        raise RuntimeError(
            f"PPTX->PDF conversion failed: {result.stderr.decode(errors='ignore')[:500]}"
        )
    return pdf


def pdf_to_pngs(pdf_path: str | Path, out_dir: str | Path | None = None,
                dpi: int = 90) -> list[Path]:
    """Rasterize each PDF page to PNG. Returns paths ordered by page."""
    import fitz  # PyMuPDF

    fitz.TOOLS.mupdf_display_errors(False)
    pdf = Path(pdf_path)
    out = Path(out_dir) if out_dir else pdf.parent
    out.mkdir(parents=True, exist_ok=True)

    pngs: list[Path] = []
    zoom = dpi / 72.0
    with fitz.open(str(pdf)) as doc:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            dest = out / f"slide_{i + 1:02d}.png"
            pix.save(str(dest))
            pngs.append(dest)
    return pngs


def pptx_to_pngs(pptx_path: str | Path, out_dir: str | Path | None = None,
                 dpi: int = 90) -> list[Path]:
    """Render a PPTX to one PNG per slide. Returns paths ordered by slide."""
    out = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="ppt_preview_"))
    pdf = pptx_to_pdf(pptx_path, out)
    return pdf_to_pngs(pdf, out, dpi=dpi)
