# nhs-hour-log — project TODO

Single source of truth for what is done, what is next, and what is parked.
Update this file as part of every session wrap-up (project-knowledge-updater
reads and propagates; session snapshots should reference it, not duplicate it).

Last updated: 2026-07-19 (session: F1–F6 committed, lock restored, ingest.sh
added, website scaffolded).

## Now (in order)

1. **Website v1 components** — scaffold is DONE (see Done log); next slice per
   `docs/WEBSITE_PLAN.md` §10 steps 3–4: `useHoursData` composable (fetch +
   schema gate ≥ 1.1.0 + loading/error states), then the six v1 panels
   (summary, totals, weekly, daily, methodology, integrity) wired into
   App.vue, styled per §5 (calm, NHS-adjacent, tabular numerals, WCAG-AA).
   Needs a fresh plan-gate for the component slice.
2. **Deploy** — BLOCKED on two user decisions: §7 identity/hosting (the
   dataset itself is the exposure, per BUILD_NOTES §1) and creating a GitHub
   remote (repo currently has none). Then deploy.yml + scripts/update.sh.

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

- 2026-07-19 (night): website/ scaffolded per the approved plan.md (figures in
  it refreshed to the 07-18 dataset first): Vite 8 + Vue 3.5 + TS + Tailwind
  v4.3 via @tailwindcss/vite (no v3 config files), base "/nhs-hour-log/",
  types/web-data.ts bound to the real JSON, lib/format.ts (the only
  converters), real web_data.json in public/, boilerplate stripped. Verified:
  vue-tsc clean, production build passes, preview serves the JSON at the
  Pages base path (16 808 min, integrity all true, schema 1.1.0).
- 2026-07-19 (evening): scripts/ingest.sh built and sandbox-tested (8
  scenarios: clean ingest, collision, changed/removed/backfilled historical
  rows, accept path, idempotent re-run, malformed input). Drift baseline is
  the CANONICAL CSV (last accepted state), not the newest-named export, so
  accepted corrections do not re-flag. Flags: --accept-drift, --force-export;
  env: HOURS_DOWNLOADS_DIR. Detection is header-based (Date,Start,End,
  Minutes,Hours,...), so unrelated CSVs in downloads are ignored.
- 2026-07-19 (later still): audit documents consolidated into docs/ — the two
  "copies" were not duplicates: the root file was the audit REPORT (now
  docs/logic-audit_2026-07-06.md, moved) and the docs/ file was the PROMPT
  that commissioned it (renamed docs/logic-audit-prompt_2026-07-06.md).
  Live references in audit/ repointed. Rule confirmed: non-config
  documentation lives in docs/.
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
  spreadsheet; the drift gate (scripts/ingest.sh) exists to catch this class
  of change loudly in future.
- 2026-07-06: logic audit (verdict: arithmetic correct; findings F1–F6 with
  patches; characterisation suite added under audit/).
- 2026-06-26: engine v2 built, externally audited, locked at schema 1.1.0;
  website plan written.
