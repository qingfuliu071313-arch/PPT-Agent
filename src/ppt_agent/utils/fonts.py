"""Font detection and fallback for cross-platform compatibility."""

from __future__ import annotations

import platform
import subprocess
from functools import lru_cache


# Font fallback chains by platform
_FONT_CHAINS = {
    "darwin": {
        "zh_title": ["PingFang SC", "Hiragino Sans GB", "STHeiti", "Microsoft YaHei", "Arial"],
        "zh_body": ["PingFang SC", "Hiragino Sans GB", "STHeiti", "Microsoft YaHei", "Arial"],
        "en": ["Helvetica Neue", "Calibri", "Arial", "Helvetica"],
    },
    "win32": {
        "zh_title": ["Microsoft YaHei", "SimHei", "PingFang SC", "Arial"],
        "zh_body": ["Microsoft YaHei", "SimSun", "PingFang SC", "Arial"],
        "en": ["Calibri", "Arial", "Helvetica Neue"],
    },
    "linux": {
        "zh_title": ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "Microsoft YaHei", "Arial"],
        "zh_body": ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "Microsoft YaHei", "Arial"],
        "en": ["DejaVu Sans", "Calibri", "Arial"],
    },
}


@lru_cache(maxsize=1)
def _system_fonts() -> set[str]:
    """Get available system fonts (cached)."""
    system = platform.system().lower()
    try:
        if system == "darwin":
            result = subprocess.run(
                ["fc-list", "--format=%{family}\n"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                result = subprocess.run(
                    ["system_profiler", "SPFontsDataType"],
                    capture_output=True, text=True, timeout=10,
                )
                return {line.strip().rstrip(":") for line in result.stdout.splitlines()
                        if line.strip() and not line.strip().startswith(("Location", "Type", "Copy", "Enabled", "Duplicate"))}
            return {f.strip().split(",")[0] for f in result.stdout.splitlines() if f.strip()}
        elif system == "windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
            fonts = set()
            i = 0
            while True:
                try:
                    name, _, _ = winreg.EnumValue(key, i)
                    fonts.add(name.split(" (")[0])
                    i += 1
                except OSError:
                    break
            return fonts
        else:
            result = subprocess.run(
                ["fc-list", "--format=%{family}\n"],
                capture_output=True, text=True, timeout=5,
            )
            return {f.strip().split(",")[0] for f in result.stdout.splitlines() if f.strip()}
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return set()


def _platform_key() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "darwin"
    elif system == "windows":
        return "win32"
    return "linux"


def resolve_font(role: str = "zh_body") -> str:
    """Resolve best available font for a given role.

    Roles: zh_title, zh_body, en
    """
    plat = _platform_key()
    chain = _FONT_CHAINS.get(plat, _FONT_CHAINS["darwin"]).get(role, ["Arial"])
    available = _system_fonts()

    if not available:
        return chain[0]

    for font in chain:
        if font in available:
            return font
        for sys_font in available:
            if font.lower() in sys_font.lower():
                return sys_font

    return chain[0]


def font_for_text(text: str) -> str:
    """Auto-detect whether text is primarily CJK or Latin and return appropriate font."""
    cjk_count = sum(1 for c in text if '一' <= c <= '鿿' or '　' <= c <= '〿')
    if cjk_count > len(text) * 0.3:
        return resolve_font("zh_body")
    return resolve_font("en")


def get_font_pair() -> tuple[str, str]:
    """Return (title_font, body_font) for current platform."""
    return resolve_font("zh_title"), resolve_font("zh_body")
