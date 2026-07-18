"""
fetch_topics.py

Pulls raw candidate items for each keyword using the agent-reach CLI
(https://github.com/Panniantong/Agent-Reach).

Prereqs (run once, locally, before this script works):
    pip install agent-reach
    agent-reach install
    agent-reach configure twitter-cookies "<your cookies>"   # only needed for twitter
    agent-reach doctor                                        # confirm sources are green

This script does NOT call any API directly — it shells out to whatever
CLI agent-reach has wired up (xreach, gh, yt-dlp, curl, etc.), so it
stays in sync automatically if you swap an adapter later.
"""

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def run_cli(cmd: list[str]) -> str:
    """Run a shell command and return stdout, or '' on failure."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, check=False
        )
        if result.returncode != 0:
            print(f"  [warn] command failed: {' '.join(cmd)}\n  {result.stderr[:300]}")
            return ""
        return result.stdout
    except FileNotFoundError:
        print(f"  [warn] command not found: {cmd[0]} (is agent-reach installed?)")
        return ""
    except subprocess.TimeoutExpired:
        print(f"  [warn] timed out: {' '.join(cmd)}")
        return ""


def fetch_twitter(keyword: str, limit: int) -> list[dict]:
    out = run_cli(["xreach", "search", keyword, "-n", str(limit), "--json"])
    if not out:
        return []
    try:
        items = json.loads(out)
    except json.JSONDecodeError:
        return []
    return [
        {
            "source": "twitter",
            "title": item.get("text", "")[:200],
            "url": item.get("url", ""),
            "engagement": item.get("like_count", 0) + item.get("retweet_count", 0),
            "created_at": item.get("created_at", ""),
        }
        for item in items
    ]


def fetch_reddit(keyword: str, limit: int) -> list[dict]:
    try:
        resp = requests.get(
            "https://www.reddit.com/search.json",
            params={"q": keyword, "sort": "hot", "limit": limit},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"  [warn] Reddit returned status {resp.status_code}")
            return []
        data = resp.json()
    except Exception as e:
        print(f"  [warn] Reddit request failed: {e}")
        return []
    children = data.get("data", {}).get("children", [])
    return [
        {
            "source": "reddit",
            "title": c["data"].get("title", ""),
            "url": "https://reddit.com" + c["data"].get("permalink", ""),
            "engagement": c["data"].get("score", 0) + c["data"].get("num_comments", 0),
            "created_at": datetime.fromtimestamp(
                c["data"].get("created_utc", 0), tz=timezone.utc
            ).isoformat(),
        }
        for c in children
    ]


def fetch_github(keyword: str, limit: int) -> list[dict]:
    out = run_cli(
        ["gh", "search", "repos", keyword, "--sort", "stars", "--limit", str(limit), "--json",
         "fullName,description,url,stargazersCount,updatedAt"]
    )
    if not out:
        return []
    try:
        items = json.loads(out)
    except json.JSONDecodeError:
        return []
    return [
        {
            "source": "github",
            "title": f"{item.get('fullName', '')} — {item.get('description', '') or ''}"[:200],
            "url": item.get("url", ""),
            "engagement": item.get("stargazersCount", 0),
            "created_at": item.get("updatedAt", ""),
        }
        for item in items
    ]


def fetch_youtube(keyword: str, limit: int) -> list[dict]:
    out = run_cli(
        ["yt-dlp", f"ytsearch{limit}:{keyword}", "--dump-json", "--no-download", "--flat-playlist"]
    )
    if not out:
        return []
    items = []
    for line in out.strip().split("\n"):
        try:
            v = json.loads(line)
        except json.JSONDecodeError:
            continue
        items.append(
            {
                "source": "youtube",
                "title": v.get("title", ""),
                "url": v.get("url", "") or f"https://youtube.com/watch?v={v.get('id', '')}",
                "engagement": v.get("view_count", 0) or 0,
                "created_at": v.get("upload_date", ""),
            }
        )
    return items


FETCHERS = {
    "twitter": fetch_twitter,
    "reddit": fetch_reddit,
    "github": fetch_github,
    "youtube": fetch_youtube,
}


def main():
    cfg = load_config()
    out_dir = Path(__file__).parent / cfg["output_dir"]
    out_dir.mkdir(exist_ok=True)

    all_items = []
    for keyword in cfg["keywords"]:
        print(f"Fetching: {keyword}")
        for source in cfg["sources"]:
            fetcher = FETCHERS.get(source)
            if not fetcher:
                continue
            items = fetcher(keyword, cfg["items_per_source"])
            for item in items:
                item["keyword"] = keyword
            all_items.extend(items)
            time.sleep(1)  # be polite to rate limits

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    raw_path = out_dir / f"raw_{today}.json"
    with open(raw_path, "w") as f:
        json.dump(all_items, f, indent=2)

    print(f"\nCollected {len(all_items)} items -> {raw_path}")


if __name__ == "__main__":
    main()
