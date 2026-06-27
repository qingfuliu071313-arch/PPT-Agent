"""DesignDNA-styled scientific figure rendering via matplotlib.

Native PowerPoint charts (``add_chart``) cover simple, *editable* column/bar/
line/pie charts. This module covers what native charts cannot: scatter (+
regression), error bars, box/violin, heatmaps, histograms and area plots —
rendered to a PNG styled to the deck's DesignDNA palette and CJK fonts, then
inserted as a normal image (image-first philosophy).

matplotlib is imported lazily so importing this module never slows CLI startup
or hard-fails if the optional backend is unavailable; ``render_chart`` returns
None on any failure and the renderer falls back to a placeholder frame.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ppt_agent.models import ChartData, DesignDNA

# Chart types that REQUIRE matplotlib — native add_chart cannot produce these.
SCIENTIFIC_TYPES = {
    "scatter", "regression", "errorbar", "box", "boxplot",
    "violin", "heatmap", "hist", "histogram", "area", "area_stacked",
}

_CJK_FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Microsoft/SimHei.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]

_cjk_font_name: str | None = None
_cjk_resolved = False


def needs_matplotlib(cd: ChartData | None) -> bool:
    """True when a chart must be rendered through matplotlib rather than native."""
    if cd is None:
        return False
    if (getattr(cd, "engine", "native") or "native").lower() == "matplotlib":
        return True
    return (cd.chart_type or "").lower() in SCIENTIFIC_TYPES


def _resolve_cjk_font() -> str | None:
    """Register a CJK-capable font with matplotlib; return its family name."""
    global _cjk_font_name, _cjk_resolved
    if _cjk_resolved:
        return _cjk_font_name
    _cjk_resolved = True
    try:
        from matplotlib import font_manager
    except Exception:
        return None
    for path in _CJK_FONT_CANDIDATES:
        if Path(path).exists():
            try:
                font_manager.fontManager.addfont(path)
                _cjk_font_name = font_manager.FontProperties(fname=path).get_name()
                return _cjk_font_name
            except Exception:
                continue
    return None


def _c(hex_color: str, default: str) -> str:
    h = (hex_color or default).lstrip("#")
    return "#" + h


def _palette(dna: DesignDNA) -> list[str]:
    """A categorical color cycle derived from the DesignDNA accent/primary."""
    base = [
        _c(dna.accent_color, "C00000"),
        _c(dna.primary_color, "990033"),
        _c(dna.text_muted, "666666"),
    ]
    # Extend with tints so multi-series charts don't run out of colors.
    try:
        import matplotlib.colors as mcolors

        extra = []
        for hexc in base[:2]:
            rgb = mcolors.to_rgb(hexc)
            extra.append(mcolors.to_hex([min(1.0, c + (1 - c) * 0.45) for c in rgb]))
        base += extra
    except Exception:
        pass
    return base


def render_chart(
    cd: ChartData,
    dna: DesignDNA,
    output_path: str | Path = "",
    width_in: float = 6.0,
    height_in: float = 4.0,
    dpi: int = 200,
) -> str | None:
    """Render ``cd`` to a DesignDNA-styled PNG. Returns the path or None on failure."""
    if not output_path:
        output_path = Path(tempfile.gettempdir()) / "ppt_agent_images" / "chart.png"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None

    fam = _resolve_cjk_font()
    rc = {"axes.unicode_minus": False, "figure.autolayout": True}
    if fam:
        rc["font.sans-serif"] = [fam, "DejaVu Sans"]
        rc["font.family"] = "sans-serif"

    colors = _palette(dna)
    text_color = _c(dna.text_on_light, "000000")
    muted = _c(dna.text_muted, "666666")
    ctype = (cd.chart_type or "column").lower()

    try:
        with plt.rc_context(rc):
            fig, ax = plt.subplots(figsize=(max(2.0, width_in), max(1.5, height_in)), dpi=dpi)
            fig.patch.set_facecolor("white")
            ax.set_facecolor("white")

            _dispatch(ctype, ax, cd, colors, plt)

            _style_axes(ax, cd, text_color, muted)
            if cd.title:
                ax.set_title(cd.title, color=text_color, fontsize=13, fontweight="bold", pad=10)

            fig.savefig(output_path, dpi=dpi, bbox_inches="tight",
                        facecolor="white", edgecolor="none")
            plt.close(fig)
        return str(output_path) if output_path.exists() else None
    except Exception:
        try:
            plt.close("all")
        except Exception:
            pass
        return None


def _series_pairs(cd: ChartData):
    """Yield (name, dict) for each series with a stable name."""
    for i, sr in enumerate(cd.series):
        yield sr.get("name", f"Series {i + 1}"), sr


def _dispatch(ctype: str, ax, cd: ChartData, colors: list[str], plt) -> None:
    cats = cd.categories

    if ctype in ("scatter", "regression"):
        for i, (name, sr) in enumerate(_series_pairs(cd)):
            x = sr.get("x") or list(range(len(sr.get("y", []))))
            y = sr.get("y", sr.get("values", []))
            col = colors[i % len(colors)]
            ax.scatter(x, y, label=name, color=col, s=36, alpha=0.8, edgecolors="white", linewidths=0.5)
            if ctype == "regression" or sr.get("fit"):
                _add_regression(ax, x, y, col)

    elif ctype == "errorbar":
        for i, (name, sr) in enumerate(_series_pairs(cd)):
            x = sr.get("x") or (cats if cats else list(range(len(sr.get("y", sr.get("values", []))))))
            y = sr.get("y", sr.get("values", []))
            yerr = sr.get("yerr") or sr.get("error")
            xpos = list(range(len(y))) if cats else x
            ax.errorbar(xpos, y, yerr=yerr, label=name, color=colors[i % len(colors)],
                        marker="o", capsize=4, linewidth=1.6, markersize=5)
        if cats:
            ax.set_xticks(range(len(cats)))
            ax.set_xticklabels(cats)

    elif ctype in ("box", "boxplot", "violin"):
        data = [sr.get("values", sr.get("y", [])) for _, sr in _series_pairs(cd)]
        labels = [n for n, _ in _series_pairs(cd)] or cats
        if ctype == "violin":
            parts = ax.violinplot(data, showmeans=True)
            for j, body in enumerate(parts["bodies"]):
                body.set_facecolor(colors[j % len(colors)])
                body.set_alpha(0.6)
            ax.set_xticks(range(1, len(labels) + 1))
            ax.set_xticklabels(labels)
        else:
            bp = ax.boxplot(data, patch_artist=True)
            for j, box in enumerate(bp["boxes"]):
                box.set_facecolor(colors[j % len(colors)])
                box.set_alpha(0.6)
            if labels:
                ax.set_xticks(range(1, len(labels) + 1))
                ax.set_xticklabels(labels)

    elif ctype in ("hist", "histogram"):
        for i, (name, sr) in enumerate(_series_pairs(cd)):
            vals = sr.get("values", sr.get("y", []))
            ax.hist(vals, bins=sr.get("bins", 20), label=name,
                    color=colors[i % len(colors)], alpha=0.65, edgecolor="white")

    elif ctype == "heatmap":
        matrix = [sr.get("values", []) for _, sr in _series_pairs(cd)]
        cmap = cd.colormap or "RdBu_r"
        im = ax.imshow(matrix, aspect="auto", cmap=cmap)
        ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        if cats:
            ax.set_xticks(range(len(cats)))
            ax.set_xticklabels(cats, rotation=45, ha="right")
        rows = cd.row_labels or [n for n, _ in _series_pairs(cd)]
        if rows:
            ax.set_yticks(range(len(rows)))
            ax.set_yticklabels(rows)
        ax.grid(False)

    elif ctype in ("area", "area_stacked"):
        xpos = list(range(len(cats))) if cats else None
        stack = ctype == "area_stacked"
        bottom = None
        for i, (name, sr) in enumerate(_series_pairs(cd)):
            y = sr.get("values", sr.get("y", []))
            x = xpos if xpos is not None else list(range(len(y)))
            if stack:
                base = bottom if bottom is not None else [0] * len(y)
                ax.fill_between(x, base, [b + v for b, v in zip(base, y)],
                                label=name, color=colors[i % len(colors)], alpha=0.7)
                bottom = [b + v for b, v in zip(base, y)]
            else:
                ax.fill_between(x, y, label=name, color=colors[i % len(colors)], alpha=0.5)
                ax.plot(x, y, color=colors[i % len(colors)], linewidth=1.6)
        if cats:
            ax.set_xticks(range(len(cats)))
            ax.set_xticklabels(cats)

    elif ctype in ("line",):
        xpos = list(range(len(cats))) if cats else None
        for i, (name, sr) in enumerate(_series_pairs(cd)):
            y = sr.get("values", sr.get("y", []))
            x = xpos if xpos is not None else list(range(len(y)))
            ax.plot(x, y, label=name, color=colors[i % len(colors)], marker="o", linewidth=1.8)
        if cats:
            ax.set_xticks(range(len(cats)))
            ax.set_xticklabels(cats)

    else:  # bar / column fallback (grouped)
        import numpy as np

        names = [n for n, _ in _series_pairs(cd)]
        n = max(1, len(names))
        idx = np.arange(len(cats) if cats else 0)
        bw = 0.8 / n
        for i, (name, sr) in enumerate(_series_pairs(cd)):
            y = sr.get("values", sr.get("y", []))
            ax.bar(idx + i * bw, y, bw, label=name, color=colors[i % len(colors)])
        if cats:
            ax.set_xticks(idx + bw * (n - 1) / 2)
            ax.set_xticklabels(cats)


def _add_regression(ax, x, y, color) -> None:
    try:
        import numpy as np

        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if len(x) < 2:
            return
        slope, intercept = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 50)
        ax.plot(xs, slope * xs + intercept, color=color, linewidth=1.6, linestyle="--")
        ss_res = np.sum((y - (slope * x + intercept)) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
        ax.text(0.04, 0.94, f"$R^2$ = {r2:.3f}", transform=ax.transAxes,
                fontsize=10, color=color, va="top")
    except Exception:
        pass


def _style_axes(ax, cd: ChartData, text_color: str, muted: str) -> None:
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(muted)
    ax.tick_params(colors=text_color, labelsize=10)
    ax.yaxis.label.set_color(text_color)
    ax.xaxis.label.set_color(text_color)
    if cd.x_axis_title:
        ax.set_xlabel(cd.x_axis_title, fontsize=11)
    if cd.y_axis_title:
        ax.set_ylabel(cd.y_axis_title, fontsize=11)
    ax.grid(True, axis="y", color=muted, alpha=0.18, linewidth=0.6)
    handles, _ = ax.get_legend_handles_labels()
    if len(handles) > 1 or (handles and (cd.series and cd.series[0].get("name"))):
        leg = ax.legend(frameon=False, fontsize=9, labelcolor=text_color)
        if leg:
            leg.set_zorder(5)
