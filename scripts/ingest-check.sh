#!/usr/bin/env bash
# ingest-check.sh -- run scripts/ingest.sh, then check the result before
# anything is published. Never commits and never pushes: on success it prints
# the git commands and stops, so a human still looks at the figures first.
#
# Usage: scripts/ingest-check.sh [--accept-drift] [path/to/export.csv]
#        (arguments are passed straight through to ingest.sh)
# Env:   HOURS_DOWNLOADS_DIR  source folder, honoured by ingest.sh
#        REPO                 repo root override, for testing against a copy
set -euo pipefail

# Resolve repo root from this script's own location (survives a symlink).
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
REPO="${REPO:-$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)}"
cd "$REPO"

before="$(python3 -c "
import json
d = json.load(open('engine_v2/web_data.json'))['content']
print(d['totals']['total_minutes'], 'min /', len(d['daily']), 'days / to', d['period']['end'])
")"

set +e
scripts/ingest.sh "$@"
ingest_rc=$?
set -e

if [ "$ingest_rc" -ne 0 ]; then
    echo
    echo "──────────────── ingest stopped ────────────────"
    echo "Nothing was published, and no figures changed. Read the message above:"
    echo "it is either a past day that changed (re-run with --accept-drift only if"
    echo "the correction is real) or a figure the engine would not stand behind."
    echo
    echo "regen.sh builds into a temporary file and only puts it in place once the"
    echo "checks pass, so engine_v2/web_data.json and the published copy are both"
    echo "exactly as they were. Nothing to undo there."
    echo
    echo "Two things may still have moved before the stop, so check:"
    echo
    echo "  git -C \"$REPO\" status --short"
    echo
    echo "An export may be sitting in data/exports/ (delete it if the file was"
    echo "rejected, keep it if you re-run with --accept-drift), and the canonical"
    echo "CSV may already have been replaced - restore it with:"
    echo
    echo "  git -C \"$REPO\" checkout -- engine_v2/data"
    exit 1
fi

echo
echo "──────────────── checks ────────────────"
fail=0

if diff -q engine_v2/web_data.json website/public/web_data.json >/dev/null; then
    echo "PASS  the published copy matches the engine"
else
    echo "FAIL  website/public/web_data.json differs from engine_v2/web_data.json"
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
print(f"      schema {d['meta']['schema_version']}, "
      f"{c['period']['start']} to {c['period']['end']}")
print(f"      {c['totals']['total_minutes']} min over {len(c['daily'])} days")
print(f"      bands {c['totals']['minutes_by_band']}")
sys.exit(1 if (bad or ig['warnings']) else 0)
PY
then
    :
else
    fail=1
fi

newest="$(command ls -1t data/exports/hours_export_*.csv | head -1)"
case "$(basename "$newest")" in
    hours_export_*_covers-to-*.csv)
        echo "PASS  archived as $(basename "$newest")" ;;
    *)
        echo "FAIL  newest export has an unexpected name: $(basename "$newest")"
        fail=1 ;;
esac

if git diff --quiet -- engine_v2/tests; then
    echo "PASS  frozen test fixture untouched"
else
    echo "FAIL  frozen test fixture changed - it must never be written by ingest"
    fail=1
fi

if git diff --quiet -- engine_v2/afc_hours; then
    echo "PASS  engine code untouched"
else
    echo "FAIL  engine_v2/afc_hours changed - the engine is locked"
    fail=1
fi

echo
echo "  figures before: $before"
echo "────────────────────────────────────────"

if [ "$fail" -ne 0 ]; then
    echo "SOME CHECKS FAILED - do not commit. Read the FAIL lines above."
    exit 1
fi

covers="$(basename "$newest" .csv)"
covers="${covers##*covers-to-}"
echo "ALL CHECKS PASSED. Review the figures above, then publish with:"
echo
echo "  nhs-log-deploy \"data: hours to $covers\""
echo
echo "That re-checks the figures, commits only the data files and pushes."
echo "The push IS the deploy - there is no staging site."
