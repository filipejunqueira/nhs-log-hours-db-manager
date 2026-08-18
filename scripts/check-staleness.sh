#!/usr/bin/env bash
# check-staleness.sh -- notice when the published log has gone quiet, and say so.
#
# The one thing a timer can usefully do here. Downloading the workbook is manual
# and so is publishing (the push IS the deploy, on a page anyone can read), so
# nothing on a schedule can fetch data or put it out. What it CAN do is notice
# that the site has been showing the same dates for a while, which is the way
# this actually goes wrong -- not a failing command, just a forgotten one.
#
# STRICTLY READ-ONLY. It reads the published JSON over HTTP and, if a local
# checkout is there, that checkout's copy. It writes nothing, stages nothing,
# and never runs the ingest. A reminder that edits your repo is not a reminder.
#
# Two different things get reported, because they need different actions:
#   - the LIVE page is behind    -> log some days, download the workbook, ingest
#   - LOCAL is ahead of live     -> already ingested, just never published
#
# Usage: scripts/check-staleness.sh [--force-notify]
# Env:   NHS_LOG_STALE_DAYS  how many days of silence is too many (default 7)
#        NHS_LOG_URL         published data file
#        REPO                local checkout, for the unpublished-data check
# Exit:  0 nothing to say · 1 something reported · 2 could not reach the site

set -euo pipefail

STALE_DAYS="${NHS_LOG_STALE_DAYS:-7}"
URL="${NHS_LOG_URL:-https://filipejunqueira.github.io/nhs-log-hours-db-manager/web_data.json}"
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
REPO="${REPO:-$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)}"
FORCE=0

for arg in "$@"; do
    case "$arg" in
        --force-notify) FORCE=1 ;;
        -h|--help) sed -n '2,22p' "$SCRIPT_PATH"; exit 0 ;;
        *) echo "unknown argument: $arg" >&2; exit 2 ;;
    esac
done

say() { echo "$*"; }

# notify-send is best-effort on purpose. Under a user timer the session bus is
# usually there, but if it is not, the message still reaches the journal via
# stdout and the run must not fail because a desktop notification could not be
# drawn.
notify() {
    local title="$1" body="$2"
    say "$title -- $body"
    if command -v notify-send >/dev/null 2>&1; then
        notify-send --app-name="nhs-hour-log" --urgency=normal "$title" "$body" || true
    fi
}

live_json="$(curl -fsS --max-time 20 "$URL" 2>/dev/null || true)"
if [ -z "$live_json" ]; then
    say "could not reach $URL -- not treating that as stale data"
    exit 2
fi

# The live end date and how long ago it was. Reported separately from anything
# local so a network hiccup can never read as "your log is behind".
read -r live_end live_days <<EOF
$(printf '%s' "$live_json" | python3 -c "
import datetime, json, sys
d = json.load(sys.stdin)
end = d['content']['period']['end']
gap = (datetime.date.today() - datetime.date.fromisoformat(end)).days
print(end, gap)
")
EOF

local_end=""
if [ -f "$REPO/engine_v2/web_data.json" ]; then
    local_end="$(python3 -c "
import json
print(json.load(open('$REPO/engine_v2/web_data.json'))['content']['period']['end'])
")"
fi

reported=0

if [ -n "$local_end" ] && [ "$local_end" \> "$live_end" ]; then
    notify "Working-hours log: ${local_end} is ingested but not published" \
"The site still shows hours to ${live_end}. Publish with: nhs-log-deploy \"data: hours to ${local_end}\""
    reported=1
fi

if [ "$live_days" -gt "$STALE_DAYS" ] || [ "$FORCE" -eq 1 ]; then
    if [ -z "$local_end" ] || [ "$local_end" = "$live_end" ]; then
        notify "Working-hours log: nothing new for ${live_days} days" \
"The site shows hours to ${live_end}. Download the workbook, then run: nhs-log-ingest"
        reported=1
    fi
fi

if [ "$reported" -eq 0 ]; then
    say "up to date: site shows hours to ${live_end}, ${live_days} day(s) ago (threshold ${STALE_DAYS})"
    exit 0
fi
exit 1
