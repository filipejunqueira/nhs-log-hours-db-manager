#!/usr/bin/env bash
# deploy.sh -- commit the current hours data and push it, which publishes it.
#
# Pushing to main IS the deploy: .github/workflows/deploy.yml builds the site
# and GitHub Pages serves it to anyone. There is no staging site. So this runs
# two checks first and refuses to publish if either fails:
#   - the copy the website serves matches the engine's copy byte for byte
#   - the figures about to go out pass their own integrity checks, with no
#     warnings from the engine
#
# Only the data files are committed. Anything else you have changed is left
# alone and reported, so a half-finished edit elsewhere cannot ride along.
#
# Usage: deploy.sh "commit message"
# Env:   REPO   repo root override, for testing against a copy
set -euo pipefail

# Resolve repo root from this script's own location, so it works from anywhere
# (survives being reached through a symlink in ~/.local/bin).
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
REPO="${REPO:-$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)}"
cd "$REPO"

MSG="${1:-}"
if [ -z "$MSG" ]; then
    echo "usage: $(basename "$0") \"commit message\"" >&2
    echo >&2
    echo "The message is required. This pushes, and the push publishes the" >&2
    echo "figures to a page anyone can read." >&2
    exit 2
fi

DATA_PATHS=(
    data/exports
    engine_v2/data
    engine_v2/web_data.json
    website/public/web_data.json
)

echo "──────────────── before publishing ────────────────"
fail=0

if diff -q engine_v2/web_data.json website/public/web_data.json >/dev/null; then
    echo "PASS  the copy the website serves matches the engine"
else
    echo "FAIL  website/public/web_data.json differs from engine_v2/web_data.json"
    echo "      run scripts/regen.sh - the site would publish stale figures"
    fail=1
fi

if python3 - <<'PY'
import json
import sys
d = json.load(open('engine_v2/web_data.json'))
c = d['content']
ig = c['integrity']
oks = {k: v for k, v in ig.items() if k.endswith('_ok')}
bad = [k for k, v in oks.items() if not v]
print("PASS  all six integrity checks true" if not bad else f"FAIL  integrity: {bad}")
print("PASS  no engine warnings" if not ig['warnings'] else f"FAIL  warnings: {ig['warnings']}")
print(f"      about to publish: {c['totals']['total_minutes']} min over "
      f"{len(c['daily'])} days, to {c['period']['end']}")
sys.exit(1 if (bad or ig['warnings']) else 0)
PY
then
    :
else
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo
    echo "NOT PUBLISHED. Fix the FAIL lines above first."
    exit 1
fi

git add -- "${DATA_PATHS[@]}"

if git diff --cached --quiet; then
    echo
    echo "Nothing to publish: the data files are unchanged since the last commit."
    exit 0
fi

echo
echo "──────────────── staged for this commit ────────────────"
git diff --cached --stat

leftovers="$(git status --short --untracked-files=normal -- . ':(exclude)data/exports' \
    ':(exclude)engine_v2/data' ':(exclude)engine_v2/web_data.json' \
    ':(exclude)website/public/web_data.json')"
if [ -n "$leftovers" ]; then
    echo
    echo "NOT included in this commit (left exactly as they are):"
    echo "$leftovers"
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ "$BRANCH" != "main" ]; then
    echo
    echo "NOTE: you are on '$BRANCH', not main. Pushing this does NOT deploy;"
    echo "      only main triggers the Pages build."
fi

echo
git commit -qm "$MSG"
echo "committed: $(git log --oneline -1)"
git push origin "$BRANCH"

echo
if [ "$BRANCH" = "main" ]; then
    echo "Pushed. The Pages build takes a minute or two, then check:"
    echo "  https://filipejunqueira.github.io/nhs-log-hours-db-manager/"
else
    echo "Pushed '$BRANCH'. Nothing was deployed - merge to main to publish."
fi
