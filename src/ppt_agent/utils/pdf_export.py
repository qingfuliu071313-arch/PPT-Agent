"""PDF export from PPTX files.

Supports multiple backends: PowerPoint (Mac/Win) or LibreOffice.
"""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path


def export_pdf(pptx_path: str, pdf_path: str = "") -> str | None:
    """Export a PPTX file to PDF.

    Returns the PDF path on success, None on failure.
    """
    pptx = Path(pptx_path).resolve()
    if not pptx.exists():
        return None

    if not pdf_path:
        pdf_path = str(pptx.with_suffix(".pdf"))

    system = platform.system().lower()

    if system == "darwin":
        result = _export_mac_powerpoint(str(pptx), pdf_path)
        if result:
            return result
        return _export_libreoffice(str(pptx), pdf_path)
    elif system == "windows":
        return _export_win_powerpoint(str(pptx), pdf_path)
    else:
        return _export_libreoffice(str(pptx), pdf_path)


def _export_mac_powerpoint(pptx_path: str, pdf_path: str) -> str | None:
    """Use AppleScript to drive PowerPoint on Mac."""
    script = f'''
    tell application "Microsoft PowerPoint"
        open POSIX file "{pptx_path}"
        delay 2
        set theDoc to active presentation
        save theDoc in POSIX file "{pdf_path}" as save as PDF
        close theDoc
    end tell
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0 and Path(pdf_path).exists():
            return pdf_path
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _export_win_powerpoint(pptx_path: str, pdf_path: str) -> str | None:
    """Use PowerShell + COM to drive PowerPoint on Windows."""
    script = f'''
    $ppt = New-Object -ComObject PowerPoint.Application
    $pres = $ppt.Presentations.Open("{pptx_path}")
    $pres.SaveAs("{pdf_path}", 32)
    $pres.Close()
    $ppt.Quit()
    '''
    try:
        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0 and Path(pdf_path).exists():
            return pdf_path
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _export_libreoffice(pptx_path: str, pdf_path: str) -> str | None:
    """Use LibreOffice headless mode as fallback."""
    output_dir = str(Path(pdf_path).parent)
    for cmd in ["soffice", "/Applications/LibreOffice.app/Contents/MacOS/soffice",
                "libreoffice"]:
        try:
            result = subprocess.run(
                [cmd, "--headless", "--convert-to", "pdf",
                 "--outdir", output_dir, pptx_path],
                capture_output=True, text=True, timeout=60,
            )
            expected = Path(output_dir) / Path(pptx_path).with_suffix(".pdf").name
            if expected.exists():
                if str(expected) != pdf_path:
                    expected.rename(pdf_path)
                return pdf_path
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return None


def check_pdf_support() -> str:
    """Check which PDF export backend is available."""
    system = platform.system().lower()
    if system == "darwin":
        try:
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to get name of processes'],
                capture_output=True, text=True, timeout=5,
            )
            if "Microsoft PowerPoint" in result.stdout:
                return "powerpoint"
        except Exception:
            pass
    for cmd in ["soffice", "libreoffice"]:
        try:
            subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
            return "libreoffice"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return "none"
