#!/usr/bin/env bash
# ingest.sh -- bring the working-hours spreadsheet into the repo, safely.
#
# The source is normally the whole workbook. The spreadsheet exports one tab per
# CSV but downloads whole, so taking the .xlsx is the only way to get both the
# hours log and the payments ledger in one action -- and it means a recorded
# payment can no longer be missed.
#
# Pipeline (docs/TODO.md):
#   0. locate the newest .xlsx in the downloads folder that actually holds an
#      hours sheet, and convert it to CSV via scripts/xlsx_to_csv.py. A CSV may
#      still be passed explicitly and is routed by its header.
#   1. dry-run validate each derived CSV through the engine BEFORE anything is
#      copied
#   2. archive under data/exports/ as
#      hours_export_<ingest-time>_covers-to-<last-work-date>.csv, and
#      payments_export_<ingest-time>_covers-to-<last-payment-date>.csv. The
#      ingest time makes the name unique, so no export is ever overwritten and
#      the folder stays a complete record. A source byte-identical to an export
#      already held is reported, not copied again.
#   3. drift gate: changed, removed or backfilled HISTORICAL rows relative to
#      the canonical file (the last accepted state) stop the run for review;
#      re-run with --accept-drift to adopt the new file (keeping the old
#      data = simply do not re-run). This is what stops an empty payments tab
#      from quietly wiping payments that were already recorded.
#   4. copy to the canonical engine CSVs and regenerate web_data.json ONCE via
#      scripts/regen.sh, reporting the figure delta. regen.sh also refreshes
#      website/public/web_data.json, so the published page cannot silently
#      disagree with the engine.
#
# The frozen test fixture (engine_v2/tests/fixtures/) is NEVER touched here;
# re-freezing it is a separate deliberate act.
#
# Usage: scripts/ingest.sh [--accept-drift] [path/to/workbook.xlsx|export.csv]
# Env:   HOURS_DOWNLOADS_DIR  source folder (default /home/filipejunqueira/downloads)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
ENGINE="$REPO_ROOT/engine_v2"
EXPORTS="$REPO_ROOT/data/exports"
CANONICAL="$ENGINE/data/filipe_working_hours_log.csv"
PAY_CANONICAL="$ENGINE/data/payments.csv"
DOWNLOADS="${HOURS_DOWNLOADS_DIR:-/home/filipejunqueira/downloads}"
HEADER_PREFIX="Date,Start,End,Minutes,Hours,"
PAY_HEADER_PREFIX="Date,MinutesPaid"

ACCEPT_DRIFT=0
SRC=""
HOURS_SRC=""
PAY_SRC=""
WORKDIR=""

die()  { echo "ERROR: $*" >&2; exit 1; }
info() { echo "==> $*"; }

cleanup() {
    if [[ -n "$WORKDIR" && -d "$WORKDIR" ]]; then
        rm -f "$WORKDIR"/hours.csv "$WORKDIR"/payments.csv
        rmdir "$WORKDIR" 2>/dev/null || true
    fi
}
trap cleanup EXIT

parse_args() {
    for arg in "$@"; do
        case "$arg" in
            --accept-drift) ACCEPT_DRIFT=1 ;;
            --force-export)
                die "--force-export was removed: export names now include the \
ingest time, so two ingests can never collide and nothing is overwritten." ;;
            -h|--help) sed -n '2,37p' "${BASH_SOURCE[0]}"; exit 0 ;;
            -*) die "unknown flag: $arg" ;;
            *) SRC="$arg" ;;
        esac
    done
}

# Convert a workbook into WORKDIR and point the two sources at what came out.
convert_workbook() {
    local book="$1"
    WORKDIR="$(mktemp -d)"
    info "workbook: $book"
    python3 "$REPO_ROOT/scripts/xlsx_to_csv.py" "$book" "$WORKDIR" \
        || die "could not convert $book (see message above)"
    [[ -f "$WORKDIR/hours.csv" ]] || die "conversion produced no hours CSV"
    HOURS_SRC="$WORKDIR/hours.csv"
    [[ -f "$WORKDIR/payments.csv" ]] && PAY_SRC="$WORKDIR/payments.csv"
    return 0
}

# Route an explicitly given CSV by its header, exactly as find_source has always
# recognised a file by content rather than by name.
route_csv() {
    local f="$1" first
    first="$(head -1 "$f")"
    info "source: $f"
    case "$first" in
        "$HEADER_PREFIX"*)     HOURS_SRC="$f" ;;
        "$PAY_HEADER_PREFIX"*) PAY_SRC="$f" ;;
        *) die "$f has neither an hours header (${HEADER_PREFIX}...) nor a \
payments header (${PAY_HEADER_PREFIX},...)" ;;
    esac
}

resolve_sources() {
    if [[ -n "$SRC" ]]; then
        [[ -f "$SRC" ]] || die "source file not found: $SRC"
        case "$SRC" in
            *.xlsx|*.xlsm) convert_workbook "$SRC" ;;
            *)             route_csv "$SRC" ;;
        esac
        return 0
    fi

    [[ -d "$DOWNLOADS" ]] || die "downloads folder not found: $DOWNLOADS"

    # The downloads folder holds unrelated spreadsheets, so "the newest .xlsx"
    # is not good enough -- ask the converter whether each one actually has an
    # hours sheet. The header rule lives there and only there.
    local newest="" f
    for f in "$DOWNLOADS"/*.xlsx "$DOWNLOADS"/*.xlsm; do
        [[ -f "$f" ]] || continue
        python3 "$REPO_ROOT/scripts/xlsx_to_csv.py" --probe "$f" >/dev/null 2>&1 || continue
        if [[ -z "$newest" || "$f" -nt "$newest" ]]; then newest="$f"; fi
    done
    [[ -n "$newest" ]] || die "no working-hours workbook (an .xlsx with a \
Date/Start/End/Minutes/Hours sheet) in $DOWNLOADS. A single CSV can still be \
passed as an argument."
    convert_workbook "$newest"
}

# ─── validation ─────────────────────────────────────────────────────────────
# Both probes dry-run the engine on a derived file and die with the engine's own
# row-numbered message on malformed input, before anything is copied.

# Prints "<latest-iso-date> <rows> <total-min>".
probe() {
    PYTHONPATH="$ENGINE" python3 - "$HOURS_SRC" <<'EOF'
import sys
from afc_hours import core
res = core.compute_from_csv(sys.argv[1])
latest = max(d.date for d in res.days)
print(latest.isoformat(), len(res.days), res.totals.total_min)
EOF
}

# Prints "<latest-iso-date|none> <rows> <total-minutes-paid>". A payments file
# with no rows is LEGAL -- it is today's real state -- so this must not copy
# core.compute()'s "no working days in input" hard error.
probe_payments() {
    PYTHONPATH="$ENGINE" python3 - "$PAY_SRC" <<'EOF'
import sys
from afc_hours import payments
ps = payments.ingest_payments_csv(sys.argv[1])
if ps:
    print(max(p.date for p in ps).isoformat(), len(ps), sum(p.minutes_paid for p in ps))
else:
    print("none", 0, 0)
EOF
}

# ─── drift ──────────────────────────────────────────────────────────────────
# Compare the new file against the last accepted state using the engine's own
# parser. Exit 0 = no historical drift; exit 3 = drift (rows printed).

drift_check() {
    local previous="$1"
    PYTHONPATH="$ENGINE" python3 - "$previous" "$HOURS_SRC" <<'EOF'
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

# Payments drift compares date -> sorted minutes. The Note is deliberately NOT
# compared: it never reaches web_data.json, so editing one moves no figure and
# must not stop an ingest. This is also what stands between an empty payments
# tab and silently wiping payments that were already recorded -- every row shows
# up as REMOVED.
drift_check_payments() {
    local previous="$1"
    PYTHONPATH="$ENGINE" python3 - "$previous" "$PAY_SRC" <<'EOF'
import sys
from afc_hours import payments

def by_date(path):
    rows = {}
    for p in payments.ingest_payments_csv(path):
        rows.setdefault(p.date, []).append(p.minutes_paid)
    return {d: sorted(v) for d, v in rows.items()}

def fmt(mins):
    return ", ".join(f"{m} min" for m in mins)

old, new = by_date(sys.argv[1]), by_date(sys.argv[2])
if not old:
    print(f"no payments recorded yet in {sys.argv[1]}; nothing to drift against")
    sys.exit(0)
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
      f"({sum(len(v) for v in new.values()) - sum(len(v) for v in old.values()):+d} payments)")
EOF
}

# ─── archive ────────────────────────────────────────────────────────────────
# Is this exact file already in the archive? Compare against every export held,
# not just one expected name: the name carries the ingest time, so a repeat of
# the same export would otherwise get a second copy under a new name every run.
# With the payments tab empty, every run derives the same header-only CSV, so
# this is what stops data/exports/ filling with identical files.
already_archived() {
    local src="$1" f
    for f in "$EXPORTS"/*.csv; do
        [[ -f "$f" ]] || continue
        if cmp -s "$src" "$f"; then echo "$f"; return 0; fi
    done
    return 0
}

archive_export() {
    local src="$1" prefix="$2" covers="$3" already stamp target
    already="$(already_archived "$src")"
    if [[ -n "$already" ]]; then
        info "already archived: byte-identical to $(basename "$already") — no second copy made"
        return 0
    fi
    stamp="$(date +%Y-%m-%d_%H%M)"
    target="$EXPORTS/${prefix}_export_${stamp}_covers-to-${covers}.csv"
    if [[ -e "$target" ]]; then
        stamp="$(date +%Y-%m-%d_%H%M%S)"
        target="$EXPORTS/${prefix}_export_${stamp}_covers-to-${covers}.csv"
    fi
    if [[ -e "$target" ]]; then
        die "refusing to overwrite $target (two ingests within the same second?)"
    fi
    cp -f "$src" "$target"
    info "export archived: $(basename "$target")"
}

# ─── the two ingest paths ───────────────────────────────────────────────────

ingest_hours() {
    local probe_out latest rows total drift_out
    probe_out="$(probe)" || die "engine validation failed (see message above)"
    read -r latest rows total <<< "$probe_out"
    info "hours validated: $rows rows, $total min, latest entry $latest"

    mkdir -p "$EXPORTS"
    if [[ -f "$CANONICAL" ]]; then
        drift_out=""
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

    archive_export "$HOURS_SRC" "hours" "$latest"
    cp -f "$HOURS_SRC" "$CANONICAL"
    info "canonical hours CSV updated"
}

ingest_payments() {
    local probe_out latest rows total drift_out
    probe_out="$(probe_payments)" || die "payments validation failed (see message above)"
    read -r latest rows total <<< "$probe_out"
    if [[ "$rows" -eq 0 ]]; then
        info "payments validated: no payments recorded yet"
    else
        info "payments validated: $rows payments, $total min, latest $latest"
    fi

    mkdir -p "$EXPORTS"
    if [[ -f "$PAY_CANONICAL" ]]; then
        drift_out=""
        if ! drift_out="$(drift_check_payments "$PAY_CANONICAL")"; then
            echo "$drift_out"
            [[ "$ACCEPT_DRIFT" -eq 1 ]] || die "recorded payments differ from \
the last accepted state. Review the lines above: a REMOVED line usually means \
the payments tab was exported before it was filled in, which would wipe \
payments already recorded. To adopt the new file anyway, re-run with \
--accept-drift and note the reason in the commit message."
            info "payments drift ACCEPTED (--accept-drift); record the reason in the commit message"
        else
            echo "$drift_out"
        fi
    else
        info "no canonical payments CSV yet; skipping drift gate"
    fi

    archive_export "$PAY_SRC" "payments" "$latest"
    cp -f "$PAY_SRC" "$PAY_CANONICAL"
    info "canonical payments CSV updated"
}

main() {
    parse_args "$@"
    resolve_sources

    [[ -n "$HOURS_SRC" || -n "$PAY_SRC" ]] || die "nothing to ingest"

    local before="none"
    if [[ -f "$ENGINE/web_data.json" ]]; then
        before="$(PYTHONPATH="$ENGINE" python3 -c "
import json
c = json.load(open('$ENGINE/web_data.json'))['content']
print(c['totals']['total_minutes'], 'min /', len(c['daily']), 'days /', c['period']['end'])")"
    fi

    # Written as full ifs, not `[[ ... ]] && cmd`: under `set -e` a standalone
    # && list whose test fails returns 1 and kills the script, which would make
    # a payments-only ingest abort silently right here.
    if [[ -n "$HOURS_SRC" ]]; then ingest_hours; fi
    if [[ -n "$PAY_SRC" ]]; then ingest_payments; fi

    # One regeneration, after both canonical files are in place, so the run
    # never leaves an intermediate state on disk.
    bash "$REPO_ROOT/scripts/regen.sh"

    echo
    info "figures before: $before"
    info "next: review the figures above, then commit and push to publish:"
    info "  git add data/exports engine_v2/data engine_v2/web_data.json website/public/web_data.json"
    info "  git commit && git push        # the push IS the deploy - no staging site"
    info "the frozen test fixture was NOT touched (re-freeze deliberately if wanted)"
}

main "$@"
