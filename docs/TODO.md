# nhs-hour-log — project TODO

Single source of truth for what is done, what is next, and what is parked.
Update this file as part of every session wrap-up (project-knowledge-updater
reads and propagates; session snapshots should reference it, not duplicate it).

Last updated: 2026-07-29 (session: ingest pipeline closed - regen.sh now
copies to website/public, exports archived under collision-proof names).

## Now (in order)

1. **Website improvements** (user request 2026-07-19, needs planning + a
   plan-gate; both likely need engine schema 1.2.0 since aggregation belongs
   in the engine, not the browser):
   - per-MONTH breakdown (candidate: engine emits a `monthly` array
     mirroring `weekly`);
   - "hours not yet paid by payroll" (needs a paid-up-to marker as input —
     where does the user record what payroll has processed? Design question).
2. **scripts/update.sh** — the remaining automation. The "copy to
   website/public" link is DONE (2026-07-29: regen.sh does it), so what is
   left is the headless xlsx→csv conversion and the cron wrapper
   (BUILD_NOTES §5 caveats: non-interactive git auth, failures made visible).
   Committing and pushing stays deliberately manual — the push publishes.

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
- **Schema 1.2.0 (next deliberate engine lock-lift)**: emit
  `above_contract_minutes` so the header figure comes from the engine and the
  sanctioned `sumMinutes` in format.ts is deleted (decision of 2026-07-19:
  option a now, c later).
- Stale `-isation` filename references in `audit/README.md:32` and the
  characterisation suite's own docstring (cosmetic; run command shown is wrong).
- Start using `notes/snapshots/` in this repo (end sessions with
  /session-wrapup) so snapshot-restore finds snapshots without guesswork.
- **Unverified test claim**: the 2026-07-19 Done-log entry below says
  useHoursData's schema gate was "unit-tested 11 cases," but no test
  framework or test file exists anywhere in `website/` (no vitest,
  no `@vue/test-utils`, no `*.spec.*`/`*.test.*`). Actual verification was
  manual (`vite preview` + curl against a hand-crafted bad-schema fixture).
  Reconcile the wording, or add real tests, later (flagged 2026-07-21).

## Done log

- 2026-07-29: ingest pipeline closed, two gaps found by walking the export →
  live-site path. (a) `regen.sh` now copies `engine_v2/web_data.json` to
  `website/public/web_data.json` after the integrity checks pass. Before this
  the copy was a hand step nobody automated — a leftover from 26 June when
  `website/` did not exist — so the engine could be current while the published
  page showed old figures, with no error anywhere. (b) `ingest.sh` archives
  exports as `hours_export_<ingest-time>_covers-to-<last-work-date>.csv`. The
  old name was the last work date alone, so two exports taken weeks apart
  collided if no new days were added, and the documented answer
  (`--force-export`) overwrote the earlier file. That flag is now removed and
  exits with an explanation. Re-ingesting an identical file reports the match
  instead of making a duplicate. Note: the two 19-July exports are named by
  download date under the old hand-naming, and `hours_export_2026-07-18.csv`
  actually ends 14 Jul — recorded in the new `data/exports/README.md`, not
  renamed. Verified against a throwaway copy of the repo: 6 scenarios plus all
  6 invariants, including that a failed integrity check cannot reach the
  published file, and that the same CSV still yields identical content
  (16 808 min unchanged). (c) follow-on, found while testing: regen.sh wrote
  `web_data.json` and validated it afterwards, so a rejected run left the
  working tree holding data the engine refused, with the two copies
  disagreeing until someone ran `git checkout`. It now builds into
  `web_data.json.tmp` and renames it into place only once the checks pass,
  with a trap removing the temporary file on any exit. Verified: a run
  rejected for a `Minutes` typo leaves both copies with an identical checksum,
  no leftover temporary file, and nothing at all in `git status`. Note that a
  failed *ingest* can still leave the canonical CSV replaced and an export
  archived — those happen before regen runs. (d) `scripts/ingest-check.sh`
  added: runs ingest.sh then checks the result (published copy matches the
  engine, integrity clean, export named correctly, frozen fixture and engine
  code untouched). Never commits or pushes — prints the commands and stops.
  On a stop it says exactly what did and did not move.
- 2026-07-28: code-review follow-ups on the v1.1 components (website 1.3.0).
  Band and clock-class key names now live in one place (`BANDS`/`CLASSES` in
  format.ts) instead of five, with the label maps typed against them so a key
  added without a label is a compile error — verified by deliberately breaking
  it. New `lib/validate.ts` checks the data's shape, not just its version
  number: a missing content block now reaches the existing error panel instead
  of blanking the page, and a band or clock class the page does not recognise
  renders everything it does understand above an amber banner (user decision:
  warn, never refuse — a future engine release must not be able to take the
  live page down). Percentage columns go through one formatter (0.90% / 0.00%,
  previously 0.9% / 0%). Cumulative chart plots hours rather than minutes so
  the axis reads 0/50/…/300 h, and gained a screen-reader summary — the
  running total appears in no table on the page. Verified: `vue-tsc -b` clean,
  build passes, grep audit clean, three-fixture headless-browser check (real
  data / unknown class / missing block). **Gotcha recorded: `npx vue-tsc
  --noEmit` checks ZERO files here** — the root tsconfig.json is a
  references-only solution file, so it always exits 0. Use `vue-tsc -b`.
- 2026-07-21: v1.1 components shipped — CrossTab, CumulativeChart (chart.js +
  vue-chartjs, user-decided over a hand-rolled SVG), StatsPanel, wired into
  App.vue after IntegrityPanel. Bug caught in verification: `minuteToClock`
  assumed integer minutes; `mean_start_minute`/`mean_end_minute` are
  non-integer averages, so it was fixed to round first. Website app version
  introduced (distinct from the engine's schema_version): package.json
  1.2.0, injected at build time via `vite.config.ts` → `__APP_VERSION__`,
  shown in the page footer. Verified: vue-tsc clean, build passes, grep
  audit clean, headless-browser render (Playwright + Chromium, installed
  locally for this) cross-checked every new value against the raw JSON,
  user eyeballed a full-page screenshot. Pushed to main for GitHub Actions
  to deploy; live-site check is the user's own next step.
- 2026-07-19 (SITE LIVE): pushed to git@github.com:filipejunqueira/
  nhs-log-hours-db-manager.git over SSH (§7 decided by user: public repo +
  public Pages). vite base fixed to /nhs-log-hours-db-manager/. deploy.yml
  added; actions bumped to node24-era majors (checkout v7, setup-node v7,
  configure-pages v6, upload/deploy-pages v5; build on Node 24) after a
  node20 deprecation warning. Pages source was auto-enabled as legacy
  Jekyll — user flipped it to GitHub Actions. VERIFIED LIVE:
  https://filipejunqueira.github.io/nhs-log-hours-db-manager/ serves the
  Vue app and web_data.json (16 808 min, schema 1.1.0). User confirmed the
  local render looks good; the deployed site is the same build.
- 2026-07-19 (night, later): website v1 components built per approved plan.md:
  useHoursData (fetch + schema gate ≥ 1.1.0 + loading/error states, gate
  unit-tested 11 cases), six panels (summary, totals, weekly incl. baseline
  flag affordance, daily, methodology, integrity) wired into App.vue, NHS-blue
  theme token, tabular numerals, semantic tables. Header shows hours above
  contract via sanctioned sumMinutes (user decision: audience is non-technical
  payroll; principle restated in CLAUDE.md — engine determines every hours
  figure, browser only re-presents). Verified: vue-tsc clean, build passes,
  grep audit (arithmetic only in format.ts), served JSON exact. Rendered DOM
  awaits user eyeball.
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
