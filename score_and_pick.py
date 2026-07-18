"""
score_and_pick.py

Reads today's raw_<date>.json, does a cheap engagement+recency pre-filter,
then asks Grok to pick the final top N topics with captions, hashtags, and
image generation prompts.

Prereqs:
    pip install groq python-dotenv pyyaml
    GROQ_API_KEY in .env file
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
import yaml
from groq import Groq

load_dotenv()

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_seen_topics(out_dir: Path) -> set:
    seen_path = out_dir / "seen_topics.json"
    if seen_path.exists():
        with open(seen_path) as f:
            return set(json.load(f))
    return set()


def save_seen_topics(out_dir: Path, seen: set):
    seen_path = out_dir / "seen_topics.json"
    with open(seen_path, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def prefilter(items: list[dict], keep: int = 25) -> list[dict]:
    def score(item):
        return item.get("engagement", 0) or 0
    return sorted(items, key=score, reverse=True)[:keep]


def ask_grok_to_pick(items: list[dict], n: int, seen: set) -> list[dict]:
    client = Groq()

    listing = "\n".join(
        f"{i+1}. [{item['source']}] {item['title']} "
        f"(engagement: {item.get('engagement', 0)}, keyword: {item.get('keyword')}) "
        f"url: {item.get('url')}"
        for i, item in enumerate(items)
    )

    seen_note = ""
    if seen:
        seen_list = "\n".join(f"- {t}" for t in sorted(seen))
        seen_note = f"\n\nAVOID these previously used topics:\n{seen_list}"

    prompt = f"""You're a content strategist for HexaLogic, a web development and AI
automation agency (services: web/app dev, AI chatbots, cold email automation,
WhatsApp/Instagram automation). Below are {len(items)} candidate items scraped
today from Reddit, GitHub, and YouTube.

Pick the {n} BEST topics for a LinkedIn/Instagram post aimed at small-business
owners and founders interested in AI automation. Prioritize items that are
genuinely timely/hot, relevant to HexaLogic's services, and have a clear
angle — not just high engagement.
{seen_note}

For each topic provide ALL of these fields:
- title: short catchy title
- source_url: link to the original item
- why_hot: one sentence why it's trending
- content_angle: one sentence post angle
- caption: a ready-to-post caption for LinkedIn/Instagram (2-3 sentences, engaging, ends with a call to action)
- hashtags: 8-10 relevant hashtags as a single string, e.g. "#AI #Automation #..."
- image_prompt: a detailed image generation prompt (40-60 words) describing a visually striking social media image for this topic. Be specific about composition, colors, style, mood, and elements. Works with any image generator (DALL-E, Midjourney, Stable Diffusion, etc.)

Candidates:
{listing}

Respond ONLY with a JSON array, no markdown fences, no preamble, in this exact shape:
[
  {{"title": "...", "source_url": "...", "why_hot": "...", "content_angle": "...", "caption": "...", "hashtags": "#a #b #c ...", "image_prompt": "..."}},
  ...
]
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.choices[0].message.content.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def main():
    cfg = load_config()
    out_dir = Path(__file__).parent / cfg["output_dir"]
    out_dir.mkdir(exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    raw_path = out_dir / f"raw_{today}.json"
    if not raw_path.exists():
        print(f"No raw file for today at {raw_path}. Run fetch_topics.py first.")
        return

    with open(raw_path) as f:
        items = json.load(f)

    if not items:
        print("No items collected today — nothing to score.")
        return

    seen = load_seen_topics(out_dir)
    filtered = prefilter(items, keep=25)
    picks = ask_grok_to_pick(filtered, cfg["topics_per_day"], seen)

    picks_path = out_dir / f"picks_{today}.json"
    with open(picks_path, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, ensure_ascii=False)

    for pick in picks:
        seen.add(pick.get("title", ""))
    save_seen_topics(out_dir, seen)

    print(f"Picked {len(picks)} topics -> {picks_path}")


if __name__ == "__main__":
    main()
