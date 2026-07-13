#!/bin/bash
# Double-click to launch ContentCoder: starts the server if needed, then
# opens the app in your default browser.

PYTHON="/opt/anaconda3/envs/strategic_plans/bin/python"
APP_DIR="/Users/kylie.anglin/strategic_plans/contentcoder"
URL="http://127.0.0.1:8321"

if ! curl -s -o /dev/null --max-time 1 "$URL"; then
    echo "Starting ContentCoder server..."
    cd "$APP_DIR" || exit 1
    nohup "$PYTHON" server.py >> "$HOME/Library/Logs/contentcoder.log" 2>&1 &
    for _ in $(seq 1 30); do
        curl -s -o /dev/null --max-time 1 "$URL" && break
        sleep 0.5
    done
fi

open "$URL"
echo "ContentCoder is running at $URL (log: ~/Library/Logs/contentcoder.log)"
echo "You can close this window."
