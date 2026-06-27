"""Generate HTML preview cards for the PPT-Agent theme system.

Each card is a self-contained 16:9 mini-slide mockup that applies one theme's
colors and fonts, plus a swatch row. Output goes to design_system_build/, ready
to push to a Claude Design project via /design-sync. Every preview's first line
carries an @dsCard marker so the Design System pane indexes it automatically.
"""

from __future__ import annotations

import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from ppt_agent.themes import THEMES  # noqa: E402

BUILD = Path(__file__).resolve().parent.parent / "design_system_build"
CARDS = BUILD / "ui_kits" / "ppt-themes"

# Web-safe font stacks mapped from the PPT (CJK) fonts.
FONT_STACK = {
    "Microsoft YaHei": '"Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", sans-serif',
    "微软雅黑": '"Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", sans-serif',
    "Times New Roman": '"Times New Roman", Georgia, serif',
}


def stack(font: str) -> str:
    return FONT_STACK.get(font, f'"{font}", sans-serif')


def card_html(key: str, t: dict) -> str:
    p = f"#{t['primary']}"
    sec = f"#{t['secondary']}"
    acc = f"#{t['accent']}"
    td = f"#{t['text_dark']}"
    tl = f"#{t['text_light']}"
    tm = f"#{t['muted']}"
    title_font = stack(t["font_title"])
    body_font = stack(t["font_body"])
    swatches = "".join(
        f'<div class="sw"><span style="background:{c}"></span><code>{lbl}</code></div>'
        for lbl, c in [("primary", p), ("secondary", sec), ("accent", acc),
                       ("text", td), ("muted", tm)]
    )
    return f"""<!-- @dsCard group="PPT Themes" name="{t['name']} / {key}" subtitle="主色 {p} · 强调 {acc} · {t['font_title']}" -->
<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>{t['name']} — {key}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#e9ebee; font-family:{body_font}; padding:24px; }}
  .wrap {{ width:1120px; margin:0 auto; }}
  .slide {{ width:1120px; height:630px; background:#fff; position:relative;
            box-shadow:0 6px 24px rgba(0,0,0,.14); overflow:hidden; }}
  .topbar {{ position:absolute; top:0; left:0; right:0; height:14px; background:{p}; }}
  .header {{ position:absolute; top:46px; left:0; right:0; height:78px; background:{p};
             display:flex; align-items:center; padding:0 56px; }}
  .header h1 {{ color:{tl}; font-family:{title_font}; font-size:34px; font-weight:700; }}
  .body {{ position:absolute; top:160px; left:56px; right:56px; }}
  .key {{ color:{p}; font-family:{title_font}; font-weight:700; font-size:26px;
          text-align:center; margin-bottom:26px; }}
  ul {{ list-style:none; }}
  li {{ color:{td}; font-size:21px; line-height:2.0; padding-left:22px; position:relative; }}
  li::before {{ content:""; position:absolute; left:0; top:14px; width:9px; height:9px;
                border-radius:50%; background:{acc}; }}
  .accentline {{ width:170px; height:5px; background:{acc};
                 position:absolute; left:56px; bottom:96px; }}
  .footer {{ position:absolute; bottom:0; left:0; right:0; height:60px; background:{p};
             display:flex; align-items:center; justify-content:flex-end; padding:0 40px; }}
  .footer span {{ color:{tl}; font-size:14px; opacity:.85; }}
  .chip {{ position:absolute; top:174px; right:56px; background:{sec}; color:{p};
           font-size:13px; padding:6px 14px; border-radius:20px; font-weight:600; }}
  .meta {{ width:1120px; margin:18px auto 0; display:flex; gap:10px; flex-wrap:wrap;
           align-items:center; }}
  .sw {{ display:flex; align-items:center; gap:7px; background:#fff; border:1px solid #dde;
         border-radius:8px; padding:6px 10px; }}
  .sw span {{ width:20px; height:20px; border-radius:5px; border:1px solid rgba(0,0,0,.12); }}
  .sw code {{ font-size:12px; color:#445; font-family:ui-monospace,monospace; }}
  .fonts {{ margin-left:auto; font-size:13px; color:#556; }}
</style></head>
<body><div class="wrap">
  <div class="slide">
    <div class="topbar"></div>
    <div class="header"><h1>{t['name']}主题 · 版式示例</h1></div>
    <div class="chip">PPT-Agent</div>
    <div class="body">
      <div class="key">一句话核心论点居中强调</div>
      <ul>
        <li>正文要点一：图文优先的学术排版</li>
        <li>正文要点二：主色 / 强调色 / 文字色由主题统一驱动</li>
        <li>正文要点三：标题栏、要点符号、分隔线风格一致</li>
      </ul>
    </div>
    <div class="accentline"></div>
    <div class="footer"><span>{t['name']} · {key}</span></div>
  </div>
  <div class="meta">{swatches}<div class="fonts">标题 {t['font_title']} · 正文 {t['font_body']}</div></div>
</div></body></html>
"""


def collect_themes() -> dict[str, dict]:
    out = {}
    for key, tc in THEMES.items():
        out[key] = {
            "name": tc.name, "primary": tc.primary_color,
            "secondary": tc.secondary_color, "accent": tc.accent_color,
            "text_dark": tc.text_dark, "text_light": tc.text_light,
            "muted": tc.text_muted, "font_title": tc.font_title,
            "font_body": tc.font_body,
        }
    # Add the extracted NSFC DNA as an eighth style if present.
    dna_path = Path(__file__).resolve().parent.parent / "output" / "nsfc_dna.json"
    if dna_path.exists():
        d = json.loads(dna_path.read_text())
        out["nsfc_blue"] = {
            "name": "NSFC 深蓝(提取)", "primary": d["primary_color"],
            "secondary": d["secondary_color"], "accent": d["accent_color"],
            "text_dark": d.get("text_on_light", "0E30AB"), "text_light": "FFFFFF",
            "muted": d.get("text_muted", "0E30AB"),
            "font_title": d.get("font_primary", "Times New Roman"),
            "font_body": d.get("font_secondary", "微软雅黑"),
        }
    return out


def main() -> None:
    themes = collect_themes()
    CARDS.mkdir(parents=True, exist_ok=True)
    written = []
    for key, t in themes.items():
        d = CARDS / key
        d.mkdir(parents=True, exist_ok=True)
        f = d / "preview.html"
        f.write_text(card_html(key, t), encoding="utf-8")
        written.append(str(f.relative_to(BUILD)))
    print(f"{len(written)} cards written to {BUILD}")
    for w in written:
        print("  ", w)


if __name__ == "__main__":
    main()
