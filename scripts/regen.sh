#!/usr/bin/env bash
# Regenerate engine_v2/web_data.json from the current working-hours CSV.
# Pure-stdlib engine -> no conda env needed. Safe to symlink into ~/.local/bin.
set -euo pipefail

# Resolve repo root from this script's own location (survives a symlink).
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
ENGINE="$REPO_ROOT/engine_v2"
CSV_NAME="filipe_working_hours_log.csv"
CSV="$ENGINE/data/$CSV_NAME"

[[ -f "$CSV" ]] || { echo "ERROR: CSV not found: $CSV" >&2; exit 1; }

cd "$ENGINE"
echo "Regenerating web_data.json from data/$CSV_NAME ..."
python3 -c "from afc_hours import core, emit; emit.write_json(core.compute_from_csv('data/$CSV_NAME'), 'web_data.json')"

python3 -c "
import json, sys
d = json.load(open('web_data.json'))
c = d['content']; t = c['totals']; ig = c['integrity']
oks = {k: v for k, v in ig.items() if k.endswith('_ok')}
print('  schema         ', d['meta']['schema_version'])
print('  period         ', c['period']['start'], '->', c['period']['end'])
print('  total          ', t['total_minutes'], 'min (', round(t['total_minutes']/60, 2), 'h )')
print('  bands          ', t['minutes_by_band'])
print('  classes        ', t['minutes_by_class'])
print('  within_baseline', t['unsocial_within_baseline_minutes'])
print('  integrity      ', oks)
print('  warnings       ', ig['warnings'])
bad = [k for k, v in oks.items() if not v]
if bad or ig['warnings']:
    print('INTEGRITY FAIL:', bad, ig['warnings'], file=sys.stderr); sys.exit(1)
print('OK: regenerated, all integrity checks pass.')
"

# --- deferred (the future scripts/update.sh will wrap this) ---
#  1. copy newest CSV from ~/downloads into data/ before regen
#  2. cp web_data.json -> website/public/web_data.json   (once website/ exists)
#  3. prompt: git add/commit/push to trigger the Pages deploy
