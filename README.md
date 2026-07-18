# HexaLogic Topic Scout

Daily agent that searches the internet for your keywords and picks the
2 hottest content topics, with a suggested angle, into a local HTML
dashboard.

## How it works

1. `fetch_topics.py` — pulls raw candidate posts/repos/videos per
   keyword from Twitter, Reddit, GitHub, YouTube (via the `agent-reach`
   CLI adapters).
2. `score_and_pick.py` — pre-filters by engagement, then asks Grok (Grok API) to
   pick the final top N with a "why it's hot" + content angle.
3. `generate_dashboard.py` — renders everything into
   `output/dashboard.html` (today on top, history below).
4. `run_daily.sh` — runs all three in order. Put this on a cron job.

## One-time setup

```bash
cd topic-scout
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt   # groq, pyyaml, python-dotenv

# .env file (already created with your API key)
# GROQ_API_KEY=gsk_...

# Install and configure agent-reach (search layer)
pip install agent-reach
agent-reach install
agent-reach configure twitter-cookies "<cookies from Cookie-Editor extension>"
agent-reach doctor   # confirm sources show green

# GitHub CLI auth (for the github source)
gh auth login

# yt-dlp needs no auth

# Grok API key (for scoring/picking) - set in .env file
# GROQ_API_KEY in .env
```

`requirements.txt`:
```
pyyaml
groq
python-dotenv
```

## Edit your keywords

Open `config.yaml` and change the `keywords` list — no code changes needed.

## Run it

```bash
./run_daily.sh
open output/dashboard.html   # or just double-click the file
```

## Automate it (daily at 8am)

```bash
crontab -e
# add:
0 8 * * * cd /full/path/to/topic-scout && ./run_daily.sh >> log.txt 2>&1
```

## Notes

- Twitter/Reddit access via cookies carries an account-flagging risk on
  the platform's side — use a secondary account, not your main one.
- `output/raw_<date>.json` keeps the unfiltered pull if you ever want
  to re-score with a different prompt without re-fetching.
- Swap the Grok model in `score_and_pick.py` or the prompt itself if
  you want a different tone/audience framing over time.
