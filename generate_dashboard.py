"""
generate_dashboard.py

Builds output/dashboard.html showing today's picks front-and-center,
with a scrollable history below. Open the file in any browser.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent / "config.yaml"

CARD_TEMPLATE = """
<div class="card">
  <h3>{title}</h3>
  <p class="why">{why_hot}</p>
  <p class="angle"><strong>Angle:</strong> {content_angle}</p>
  <div class="caption-box">
    <div class="box-header"><strong>Caption</strong> <button class="copy-btn" onclick="copyText(this)" data-text="{caption_html}">Copy</button></div>
    <p>{caption}</p>
  </div>
  <div class="hashtags">{hashtags}</div>
  <div class="caption-box image-box">
    <div class="box-header"><strong>Image Prompt</strong> <button class="copy-btn" onclick="copyText(this)" data-text="{image_prompt_html}">Copy</button></div>
    <p>{image_prompt}</p>
  </div>
  <a href="{source_url}" target="_blank">source →</a>
</div>
"""

DAY_TEMPLATE = """
<section class="day">
  <h2>{date}</h2>
  <div class="cards">{cards}</div>
</section>
"""

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>HexaLogic Topic Scout</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, sans-serif; background: #1A1D23; color: #F5F5F0; margin: 0; padding: 40px 20px; }}
  h1 {{ color: #B8934A; text-align: center; margin-bottom: 4px; }}
  .subtitle {{ text-align: center; color: #3B4A6B; margin-bottom: 40px; }}
  .day {{ max-width: 900px; margin: 0 auto 40px; }}
  .day h2 {{ border-bottom: 2px solid #3B4A6B; padding-bottom: 8px; }}
  .day:first-of-type h2 {{ color: #B8934A; }}
  .cards {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 16px; }}
  @media (max-width: 700px) {{ .cards {{ grid-template-columns: 1fr; }} }}
  .card {{ background: #23272f; border: 1px solid #3B4A6B; border-radius: 10px; padding: 20px; }}
  .card h3 {{ margin-top: 0; color: #F5F5F0; }}
  .why {{ color: #c9c9c9; font-size: 0.95em; }}
  .angle {{ color: #F5F5F0; }}
  .caption-box {{ background: #1A1D23; border-left: 3px solid #B8934A; padding: 10px 14px; margin: 12px 0; border-radius: 4px; font-size: 0.95em; color: #e0e0e0; }}
  .caption-box p {{ margin: 6px 0 0; }}
  .image-box {{ border-left-color: #5ba3d9; }}
  .box-header {{ display: flex; justify-content: space-between; align-items: center; }}
  .copy-btn {{ background: #3B4A6B; color: #F5F5F0; border: none; padding: 3px 10px; border-radius: 4px; cursor: pointer; font-size: 0.8em; }}
  .copy-btn:hover {{ background: #B8934A; color: #1A1D23; }}
  .copy-btn.copied {{ background: #2ea043; }}
  .hashtags {{ color: #5ba3d9; font-size: 0.85em; margin: 8px 0; word-wrap: break-word; }}
  .card a {{ color: #B8934A; text-decoration: none; font-size: 0.9em; }}
</style>
</head>
<body>
<h1>HexaLogic Topic Scout</h1>
<p class="subtitle">Daily hot topics, auto-generated</p>
{days}
<script>
function copyText(btn) {{
  const text = btn.getAttribute('data-text');
  navigator.clipboard.writeText(text).then(() => {{
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => {{ btn.textContent = 'Copy'; btn.classList.remove('copied'); }}, 2000);
  }});
}}
</script>
</body>
</html>
"""


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    cfg = load_config()
    out_dir = Path(__file__).parent / cfg["output_dir"]

    picks_files = sorted(out_dir.glob("picks_*.json"), reverse=True)
    if not picks_files:
        print("No picks yet — run fetch_topics.py then score_and_pick.py first.")
        return

    days_html = []
    for pf in picks_files:
        date = pf.stem.replace("picks_", "")
        with open(pf, encoding="utf-8") as f:
            picks = json.load(f)
        cards = "".join(
            CARD_TEMPLATE.format(
                title=p.get("title", ""),
                why_hot=p.get("why_hot", ""),
                content_angle=p.get("content_angle", ""),
                caption=p.get("caption", ""),
                hashtags=p.get("hashtags", ""),
                image_prompt=p.get("image_prompt", ""),
                caption_html=html_escape(p.get("caption", "")),
                image_prompt_html=html_escape(p.get("image_prompt", "")),
                source_url=p.get("source_url", "#"),
            )
            for p in picks
        )
        days_html.append(DAY_TEMPLATE.format(date=date, cards=cards))

    html = PAGE_TEMPLATE.format(days="".join(days_html))
    dashboard_path = out_dir / "dashboard.html"
    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard written -> {dashboard_path}")


if __name__ == "__main__":
    main()
