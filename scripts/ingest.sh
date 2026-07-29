#!/usr/bin/env bash
# ingest.sh -- bring a fresh working-hours CSV export into the repo, safely.
#
# Pipeline (docs/TODO.md):
#   1. locate the newest hours-shaped CSV in the downloads folder (or take an
#      explicit path as the last argument)
#   2. dry-run validate it through the engine BEFORE anything is copied
#   3. archive it under data/exports/ as
#      hours_export_<ingest-time>_covers-to-<last-work-date>.csv. The ingest
#      time makes the name unique, so no export is ever overwritten and the
#      folder stays a complete record. A source byte-identical to an export
#      already held is reported, not copied again.
#   4. drift gate: changed, removed or backfilled HISTORICAL rows relative to
#      the canonical CSV (the last accepted state) stop the run for review;
#      re-run with --accept-drift to adopt the new file (keeping the old
#      data = simply do not re-run)
#   5. copy to the canonical engine CSV and regenerate web_data.json via
#      scripts/regen.sh, reporting the figure delta. regen.sh also refreshes
#      website/public/web_data.json, so the published page cannot silently
#      disagree with the engine.
#
# The frozen test fixture (engine_v2/tests/fixtures/) is NEVER touched here;
# re-freezing it is a separate deliberate act.
#
# Usage: scripts/ingest.sh [--accept-drift] [path/to/export.csv]
# Env:   HOURS_DOWNLOADS_DIR  source folder (default /home/filipejunqueira/downloads)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
ENGINE="$REPO_ROOT/engine_v2"
EXPORTS="$REPO_ROOT/data/exports"
CANONICAL="$ENGINE/data/filipe_working_hours_log.csv"
DOWNLOADS="${HOURS_DOWNLOADS_DIR:-/home/filipejunqueira/downloads}"
HEADER_PREFIX="Date,Start,End,Minutes,Hours,"

ACCEPT_DRIFT=0
SRC=""

die()  { echo "ERROR: $*" >&2; exit 1; }
info() { echo "==> $*"; }

parse_args() {
    for arg in "$@"; do
        case "$arg" in
            --accept-drift) ACCEPT_DRIFT=1 ;;
            --force-export)
                die "--force-export was removed: export names now include the \
ingest time, so two ingests can never collide and nothing is overwritten." ;;
            -h|--help) sed -n '2,26p' "${BASH_SOURCE[0]}"; exit 0 ;;
            -*) die "unknown flag: $arg" ;;
            *) SRC="$arg" ;;
        esac
    done
}

find_source() {
    if [[ -n "$SRC" ]]; then
        [[ -f "$SRC" ]] || die "source file not found: $SRC"
        return
    fi
    [[ -d "$DOWNLOADS" ]] || die "downloads folder not found: $DOWNLOADS"
    local newest="" f first
    for f in "$DOWNLOADS"/*.csv; do
        [[ -f "$f" ]] || continue
        first="$(head -1 "$f")"
        case "$first" in
            "$HEADER_PREFIX"*)
                if [[ -z "$newest" || "$f" -nt "$newest" ]]; then newest="$f"; fi ;;
        esac
    done
    [[ -n "$newest" ]] || die "no hours-shaped CSV (header ${HEADER_PREFIX}...) in $DOWNLOADS"
    SRC="$newest"
}

# Dry-run the engine on the source file. Dies with the engine's own
# row-numbered message on any malformed input. On success prints
# "<latest-iso-date> <rows> <total-min>" for the caller to capture.
probe() {
    PYTHONPATH="$ENGINE" python3 - "$SRC" <<'EOF'
import sys
from afc_hours import core
res = core.compute_from_csv(sys.argv[1])
latest = max(d.date for d in res.days)
print(latest.isoformat(), len(res.days), res.totals.total_min)
EOF
}

# Compare the new file against the last accepted state using the engine's
# own parser. Exit 0 = no historical drift; exit 3 = drift (rows printed).
drift_check() {
    local previous="$1"
    PYTHONPATH="$ENGINE" python3 - "$previous" "$SRC" <<'EOF'
import sys
from afc_hours import core

def by_date(path):
    rows = {}
    for r in core.ingest_csv(path):
        rows.setdefault(r.date, []).append((r.start_min, r.end_min))
    return {d: sorted(v) for d, v in rows.items()}

def fmt(periods):
    return ", ".join(f"{s//60:02d}:{s%60:02d}-{e//60:02d}:{e%60:02d}" for s, e in periods)

old, new = by_date(sys.argv[1]), by_date(sys.argv[2])
old_max = max(old)
drift = []
for d in sorted(set(old) | set(new)):
    if d in old and d in new and old[d] != new[d]:
        drift.append(f"  CHANGED   {d}: {fmt(old[d])}  ->  {fmt(new[d])}")
    elif d in old and d not in new:
        drift.append(f"  REMOVED   {d}: {fmt(old[d])}")
    elif d not in old and d in new and d <= old_max:
        drift.append(f"  BACKFILLED {d}: {fmt(new[d])}")
if drift:
    print(f"historical drift vs {sys.argv[1]}:")
    print("\n".join(drift))
    sys.exit(3)
print(f"no historical drift vs {sys.argv[1]} "
      f"({sum(len(v) for v in new.values()) - sum(len(v) for v in old.values()):+d} rows)")
EOF
}

main() {
    parse_args "$@"
    find_source
    info "source: $SRC"

    local probe_out latest rows total
    probe_out="$(probe)" || die "engine validation failed (see message above)"
    read -r latest rows total <<< "$probe_out"
    info "validated: $rows rows, $total min, latest entry $latest"

    # Is this exact file already in the archive? Compare against every export
    # held, not just one expected name: the name now carries the ingest time,
    # so a repeat of the same export would otherwise get a second copy under a
    # new name every run.
    mkdir -p "$EXPORTS"
    local already="" f
    for f in "$EXPORTS"/*.csv; do
        [[ -f "$f" ]] || continue
        if cmp -s "$SRC" "$f"; then already="$f"; break; fi
    done

    if [[ -f "$CANONICAL" ]]; then
        local drift_out=""
        if ! drift_out="$(drift_check "$CANONICAL")"; then
            echo "$drift_out"
            [[ "$ACCEPT_DRIFT" -eq 1 ]] || die "historical rows differ from the \
last accepted state. Review the lines above: to keep the current data, stop \
here; to adopt the new file, re-run with --accept-drift and note the \
correction in the commit message."
            info "drift ACCEPTED (--accept-drift); record the reason in the commit message"
        else
            echo "$drift_out"
        fi
    else
        info "no canonical CSV yet; skipping drift gate"
    fi

    # Archive the export. The ingest time makes the name unique, so this never
    # overwrites: data/exports/ is a complete record of every distinct file
    # that has ever been the basis for published figures.
    if [[ -n "$already" ]]; then
        info "already archived: byte-identical to $(basename "$already") — no second copy made"
    else
        local stamp target
        stamp="$(date +%Y-%m-%d_%H%M)"
        target="$EXPORTS/hours_export_${stamp}_covers-to-${latest}.csv"
        if [[ -e "$target" ]]; then
            stamp="$(date +%Y-%m-%d_%H%M%S)"
            target="$EXPORTS/hours_export_${stamp}_covers-to-${latest}.csv"
        fi
        if [[ -e "$target" ]]; then
            die "refusing to overwrite $target (two ingests within the same second?)"
        fi
        cp -f "$SRC" "$target"
        info "export archived: $(basename "$target")"
    fi

    local before="none"
    if [[ -f "$ENGINE/web_data.json" ]]; then
        before="$(PYTHONPATH="$ENGINE" python3 -c "
import json
c = json.load(open('$ENGINE/web_data.json'))['content']
print(c['totals']['total_minutes'], 'min /', len(c['daily']), 'days /', c['period']['end'])")"
    fi

    cp -f "$SRC" "$CANONICAL"
    info "canonical CSV updated"
    bash "$REPO_ROOT/scripts/regen.sh"

    echo
    info "figures before: $before"
    info "next: review the figures above, then commit and push to publish:"
    info "  git add data/exports engine_v2/data engine_v2/web_data.json website/public/web_data.json"
    info "  git commit && git push        # the push IS the deploy - no staging site"
    info "the frozen test fixture was NOT touched (re-freeze deliberately if wanted)"
}

main "$@"
