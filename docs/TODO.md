# nhs-hour-log — project TODO

Single source of truth for what is done, what is next, and what is parked.
Update this file as part of every session wrap-up (project-knowledge-updater
reads and propagates; session snapshots should reference it, not duplicate it).

Last updated: 2026-07-19 (session: F1–F6 applied, committed; engine lock restored).

## Now (next session, in order)

1. **Consolidate the audit reports** — parse `logic-audit_2026-07-06.md` (root)
   and `docs/nhs_hours_logic_audit_2026-07-06.md`, derive which is current and
   correct, keep one canonical copy in `docs/`, remove or archive the other.
   General rule adopted: non-config documentation lives in `docs/`.

## Next

2. **`scripts/ingest.sh`** — the CSV intake pipeline (manual trigger for now):
   - Find the newest spreadsheet export in the downloads folder (source is an
     Excel file today, exported to CSV by hand; Google Sheets is a possible
     later switch).
   - Dry-run validate through the engine BEFORE copying anything into the repo.
   - Name the export by its latest entry date: `data/exports/hours_export_<latest-work-date>.csv`.
   - **Drift gate**: diff against the previous export on Date,Start,End,Minutes.
     Changed HISTORICAL rows (e.g. a corrected past date) must warn and stop
     for review — user chooses keep-old or adopt-new; the choice is recorded
     (commit message note). New trailing rows pass silently.
   - On acceptance: copy to `engine_v2/data/filipe_working_hours_log.csv`, run
     `scripts/regen.sh`, report figure deltas. Test fixture stays FROZEN —
     re-freezing is a separate deliberate act.
3. **Website v1** — scaffold `website/` per `docs/WEBSITE_PLAN.md` +
   `docs/BUILD_NOTES.md` (Vite vue-ts, Tailwind v4). Blocked before first
   public deploy on the §7 identity/hosting decision (user).

## Later / parked

- **Full automation**: export → ingest → regen → deploy on a ~7-day cadence.
  Note: an Excel file on the local machine cannot be reached by GitHub Actions;
  either a local cron/systemd timer drives the whole chain, or the source moves
  to Google Sheets/OneDrive first. Decide when we get there.
- **Extra typo tripwires** (engine adjacent, needs a deliberate lock-lift):
  cross-check the ignored `Hours` column (×60 vs recomputed minutes);
  plausibility warnings (>14 h days, implausible weeks).
- **`.tex` audit document**: methodology → pipeline → rules-as-law → six
  invariants with proofs → audit history → reproduction commands. Assemble
  largely from `AUDIT_BRIEF.md` and the audit reports.
- **money.py (Part ii)** and the private financial view — after the dashboard.
- Stale `-isation` filename references in `audit/README.md:32` and the
  characterisation suite's own docstring (cosmetic; run command shown is wrong).
- Start using `notes/snapshots/` in this repo (end sessions with
  /session-wrapup) so snapshot-restore finds snapshots without guesswork.

## Done log

- 2026-07-19 (later): session work committed on branch logic-audit-2026-07-06
  as six focused commits (data adoption + fixture, F1 test repoint, F2–F4
  core fixes, F5/F6 docs + audit report, web_data regen, CONTINUATION.md
  removal). Engine lock RESTORED in .claude/settings.json (deny rules back;
  backup deleted). TODO-functionality proposal drafted at
  docs/tmp_todo_functionality_proposal_v01.md (transient; not committed —
  destined for another project).
- 2026-07-19: F1–F6 applied to engine_v2 (lock temporarily lifted). Dataset
  reconciled to the 07-18 export (32 days, 1 Jun–14 Jul, 16 808 min; bands
  8528/4540/3740). All suites green: engine 67/67, characterisation 29/29.
  F2–F4 verified output-neutral (content hash identical). web_data.json
  regenerated (schema 1.1.0). Known fact: the 06-25 export disagrees with
  later data on 19 June dates — consistent with retro-corrections in the
  spreadsheet; the drift gate (Next item 2) exists to catch this class of
  change loudly in future.
- 2026-07-06: logic audit (verdict: arithmetic correct; findings F1–F6 with
  patches; characterisation suite added under audit/).
- 2026-06-26: engine v2 built, externally audited, locked at schema 1.1.0;
  website plan written.
