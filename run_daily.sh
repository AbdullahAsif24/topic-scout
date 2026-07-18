#!/usr/bin/env bash
# Runs the full pipeline: fetch -> score -> dashboard.
# Add this to cron for a fully automated daily run, e.g.:
#   crontab -e
#   0 8 * * * cd /path/to/topic-scout && ./run_daily.sh >> log.txt 2>&1
set -e
cd "$(dirname "$0")"

echo "=== $(date) : fetching ==="
python3 fetch_topics.py

echo "=== $(date) : scoring ==="
python3 score_and_pick.py

echo "=== $(date) : building dashboard ==="
python3 generate_dashboard.py

echo "=== Done. Open output/dashboard.html ==="
