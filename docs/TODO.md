# nhs-hour-log — project TODO

Single source of truth for what is done, what is next, and what is parked.
Update this file as part of every session wrap-up (project-knowledge-updater
reads and propagates; session snapshots should reference it, not duplicate it).

Last updated: 2026-08-18 (session: schema 1.2.0 went live, the pipeline learned
to read the .xlsx workbook itself, and the log was brought up to 18 August.
Now item 1 is CLOSED; only the cron wrapper is left of the automation.)

## Now (in order)

1. **Install the staleness timer** — yours to run, because it puts units in
   `~/.config/systemd/user/`, outside this repo. **Both** units must be linked:

       systemctl --user link /home/filipejunqueira/code/nhs-hour-log/scripts/systemd/nhs-log-staleness.service
       systemctl --user enable --now /home/filipejunqueira/code/nhs-hour-log/scripts/systemd/nhs-log-staleness.timer

   **Run these in your own terminal, not through Claude.** Claude's shell is
   containerised with `HOME=/home/filipejunqueira/containers/claude-home`, so
   `systemctl --user link` from there creates the symlink under the *container's*
   home and your real user systemd never sees it. Confirmed 2026-08-18: the
   command reported "Created symlink" and did nothing useful.

   Full paths on purpose, no shell variable: run one at a time these are
   separate shells, so a `U=...` set in one does not survive into the next and
   `link` quietly fails on `/nhs-log-staleness.service`. And keep each command
   on ONE line — a wrapped line gave "Too few arguments" and then tried to
   execute the path.

   **Linking the timer alone is not enough**, and it fails in a way that reads
   like a broken unit rather than a missing step: `systemctl --user enable` on
   an absolute path symlinks only *that* file, so the service the timer triggers
   is never loaded and starting it gives
   `Refusing to start, unit nhs-log-staleness.service to trigger not loaded`.
   Found the hard way 2026-08-18.

   Check it took:

       systemctl --user list-timers nhs-log-staleness.timer
       systemctl --user start nhs-log-staleness.service
       journalctl --user -u nhs-log-staleness.service -n 20

   The script and both units are built and tested. Until this is run, nothing
   reminds you — everything else about it is done.

## Later / parked

- **`data/payments_template.csv` is now redundant, and could mislead.** It was
  written 2026-08-10 as the spec for the payments input, back when the plan was
  to export that tab to its own CSV. Since 2026-08-18 the payments tab lives in
  the workbook and `scripts/xlsx_to_csv.py` derives `engine_v2/data/payments.csv`
  from it, so nothing reads the template any more. A future session could
  reasonably mistake it for the live path. Decide whether to delete it or retitle
  it as documentation of the column meanings — not deleted unasked, since it is
  the only place the four columns are described for a human.

- **Full automation**: export → ingest → regen → deploy on a ~7-day cadence.
  Note: an Excel file on the local machine cannot be reached by GitHub Actions;
  either a local cron/systemd timer drives the whole chain, or the source moves
  to Google Sheets/OneDrive first. Decide when we get there.
- **ruff-format the rest of engine_v2** (needs a deliberate lock-lift):
  `afc_hours/rules.py` (50 lines), `tests/test_core.py` (98) and
  `tests/test_rules.py` (56) were left unformatted on 2026-08-17 — the sweep
  that day covered only the three files schema 1.2.0 touched, which is what was
  actually approved on 2026-08-10. Doing the rest is cosmetic and
  behaviour-neutral, but `rules.py` is the rules-as-law file whose hand-aligned
  comments the audit report's line references point at, so it wants its own
  commit and a fresh look. Until then the global ruff hook will reformat
  `rules.py` the first time anything writes to it — expect that diff and let it
  happen in a commit of its own rather than folded into other work.
- **Extra typo tripwires** (engine adjacent, needs a deliberate lock-lift):
  cross-check the ignored `Hours` column (×60 vs recomputed minutes);
  plausibility warnings (>14 h days, implausible weeks).
- **`.tex` audit document**: methodology → pipeline → rules-as-law → six
  invariants with proofs → audit history → reproduction commands. Assemble
  largely from `AUDIT_BRIEF.md` and the audit reports.
- **money.py (Part ii)** and the private financial view — after the dashboard.
- ~~Schema 1.2.0 `above_contract_minutes`~~ — PROMOTED to Now item 1
  (2026-08-10): it is folded into the same lock-lift as the payments work,
  which is what finally deletes `sumMinutes` from format.ts.
- Stale `-isation` filename references in `audit/README.md:32` and the
  characterisation suite's own docstring (cosmetic; run command shown is wrong).
- ~~Start using `notes/snapshots/`~~ — DONE; two snapshots exist and
  snapshot-restore found the newest without guesswork (confirmed 2026-08-10).
  Note the failure mode it exposed: a snapshot 20 days stale described website
  1.2.0 when the repo was at 1.3.0. The ledger below is the record; a snapshot
  is only a photograph.
- **Unverified test claim**: the 2026-07-19 Done-log entry below says
  useHoursData's schema gate was "unit-tested 11 cases," but no test
  framework or test file exists anywhere in `website/` (no vitest,
  no `@vue/test-utils`, no `*.spec.*`/`*.test.*`). Actual verification was
  manual (`vite preview` + curl against a hand-crafted bad-schema file).
  Reconcile the wording, or add real tests, later (flagged 2026-07-21).

## Done log

- 2026-08-18 (last): **`scripts/update.sh` reconsidered and answered with a
  reminder instead.** Reading BUILD_NOTES §5 again after the workbook work, three
  of its four "for the daily cron to be real" caveats were already settled: the
  headless xlsx→csv conversion landed that same day, non-interactive git auth is
  moot because publishing stays manual by decision, and the Pages source is
  plainly working. Only "surface failures" was left.
  That prompted the real question, which was not "how do we write the wrapper"
  but "what can a timer usefully do here at all". The workbook only arrives in
  `~/downloads` by hand and the push publishes to a public page, so a schedule
  can neither fetch data nor put it out — the middle step it *could* automate is
  already the single command `nhs-log-ingest`. The git history shows the real
  cadence is 26 Jun, 19 Jul, 29 Jul, 2 Aug, 18 Aug: irregular, two to three
  weeks. That is not a chore being avoided, it is a thing being forgotten.
  **User decision: build a reminder, not an ingest-on-a-timer.**
  `scripts/check-staleness.sh` plus a systemd user timer at 11:00 daily,
  `Persistent=true` so a missed run fires on the next boot — which matters,
  since a reminder that only works when the laptop happens to be awake would
  miss exactly the weeks worth reminding about. It reports two different things
  because they need different actions: the live page being behind (log some
  days, ingest) and local data being ahead of live (already ingested, never
  published).
  **It is strictly read-only** — an HTTP GET and two JSON reads, no writes, no
  staging, and it never runs the ingest. That was deliberate: a timer that ran
  the ingest would rewrite `generated_at` in both copies of `web_data.json` on
  every run and leave the working tree permanently dirty even when nothing had
  changed. A reminder that edits your repo is not a reminder. Verified by
  comparing `git status` before and after.
  Six behaviours checked: fresh data stays silent and exits 0; a crossed
  threshold notifies with the real figures; **an unreachable site exits 2 and is
  never reported as staleness**; local-ahead-of-live gives the publish command
  and does not also nag about staleness; nothing is written; shellcheck clean
  and both units pass `systemd-analyze verify`.

- 2026-08-18 (later): **the pipeline reads the spreadsheet itself, and the log
  is up to date to 18 August.** Now item 1 is closed. The spreadsheet exports
  one tab per CSV but downloads whole, so `ingest.sh` now takes the `.xlsx`:
  `scripts/xlsx_to_csv.py` (`ced0012`) converts both tabs to the CSVs the engine
  already accepts, `ingest.sh` (`f495a41`) discovers the workbook by content and
  runs both derived files through the existing stages with one `regen.sh` at the
  end, and the two checking scripts (`447d17d`) gained the payments figures, a
  re-parse and a note-leak tripwire. Plan and evidence archived at
  `notes/plans/2026-08-18_workbook-ingest.md`.
  **This deleted the last quiet failure in the project**: a payments export in
  `~/downloads` used to be silently ignored — `nhs-log-ingest` reported success
  while the payment never reached the engine. With the workbook as the source
  there is no second file left to miss.
  Then `ed7924f` published the data: **58 days to 18 August, 32 055 min,
  16 210 min above contract, 270.17 h owed**, up from 47 days to 31 July and
  236.55 h. Three months now. Confirmed on the live page in a browser — owed
  panel 270.17 h, 11 weeks owing, three monthly rows, no warning banner, no page
  errors. `engine_v2/data/payments.csv` exists and is header-only, which is the
  truth: the payments tab has no rows yet.
  Four things worth keeping:
  (a) **the converter is proved against the data the engine already ate.** With
  no payments it must reproduce every value of the canonical CSV, and the engine
  must compute every day identically — 26 343 min, 47 days, 9 weeks, identical
  bands and classes. That is what makes a conversion trustworthy rather than
  plausible.
  (b) **byte-identical was not achievable, and the fault was in the old file.**
  The canonical CSV pads the Start hour in 32 of its 47 rows and not in the
  other 15, almost certainly because it was assembled from exports taken at
  different times. Measured rather than guessed: the only differing field was
  Start. The converter pads, so the one-time reformat was 12 rows, 0 of them
  substantive — and the file is consistent from here on.
  (c) **`Minutes` and `Hours` are formula cells** (116 of them).
  `openpyxl(data_only=True)` returns the last calculated value, so a workbook
  saved by something that does not evaluate formulas would arrive with them
  blank. That is a hard error naming the spreadsheet row, never a blank passed
  through.
  (d) two shell traps found by review rather than by breaking: the
  newest-export glob would have killed `ingest-check.sh` under `set -euo
  pipefail` on the first run before any payments export existed, and
  `[[ cond ]] && cmd` as a standalone statement exits the script when the test
  fails, which would have made a payments-only ingest abort silently.
- 2026-08-18: **schema 1.2.0 went LIVE** — the public page now answers the
  question this whole slice existed for: 236.55 h are owed, and since when.
  Three commits. `4fc3036` built the rendered-page check that criterion 7 had
  left unevidenced: six scenario files committed under
  `website/scripts/scenarios/`, a `scripts/build-scenarios.py` that produces
  them from the engine in memory without writing a byte inside `engine_v2/`,
  and `website/scripts/check-render.mjs` reading the rendered DOM back against
  each scenario's own JSON. 87 checks, all pass. `b261a15` recorded it in
  PLAN.md and here. `992b9dd` shipped website 1.4.1, fixing the one thing the
  check found.
  Four things worth keeping from doing it:
  (a) the builder validates itself before building — with no payments its
  payload must equal the committed `web_data.json`, and it does, so the
  scenarios are genuine engine output rather than hand-edited JSON, and
  `f36e2a3`'s regeneration is confirmed by an independent path.
  (b) the `partial` scenario pays 5 400 min, which reproduces the case
  hand-checked in the sandbox on 2026-08-10 — owed 8 793, `paid_up_to`
  2026-06-21, W26 holding 1 819 — so the shipped engine and the proven one
  agree. That is why the scenarios are committed rather than generated: after
  the next ingest the same 5 400 against a larger accrued total gives a
  different answer, and the failure would read as engine drift when nothing is
  wrong.
  (c) the check had a real bug before its first run: it counted weeks owing by
  taking `.last()` of the tables under `payments-heading`, which breaks on the
  overpaid scenario, where a ledger exists and no weeks are owing — the ledger
  table becomes the last one. Both tables now anchor on their column headings.
  (d) the check passed the `?? 0` bug it was meant to catch, because it derived
  its expectation with the same `?? 0` the component used. A page-versus-JSON
  check agrees with the component wherever the component invents a fallback.
  Reading the output found it; the assertion now pins the dash.
- 2026-08-17 (later): **the scripts and website halves of 1.2.0 landed too**,
  in two more commits the same day. `f36e2a3` taught `regen.sh` to reconcile:
  it reads `engine_v2/data/payments.csv`, reconciles against the weeks and
  hands the result to `emit.write_json`. Payments are read in the script and
  passed to `emit`, never into `core.compute()`, which takes rows only — its
  docstring calls that the structural guarantee that no flag can inflate the
  hours. A missing payments file stays legal, which is today's real state. The
  printed block gained above-contract, months, paid, owed, paid-up-to and
  payment warnings; the fail condition still reads `integrity.warnings` only,
  so an overpayment prints but never blocks publishing. Both copies of
  `web_data.json` regenerated at 1.2.0 and byte-identical (sha `4b1401a1`);
  the only changes against the previous committed JSON are the four added
  keys, three methodology lines, the schema version and `generated_at`.
  `d1e0984` then put it on the page as website 1.4.0: `OwedPanel`,
  `PaymentsTable`, `MonthlyTable`, and `sumMinutes` deleted — which
  **discharges invariant I9**, leaving `format.ts` holding nothing but minutes
  ÷ 60 and clock formatting, with the header reading the engine's
  `totals.above_contract_minutes` instead of adding up. `validate.ts` gained
  warning-level checks for a missing payments block, a missing monthly block
  and a missing `above_contract_minutes`, with `REQUIRED_BLOCKS` deliberately
  untouched so a pre-1.2.0 file still renders — it simply cannot say what is
  owed. Verified: `vue-tsc -b` clean, build passes, grep confirms no arithmetic
  outside `format.ts`, and the built site serves 1.2.0 over `vite preview`
  showing 236.55 h owed. Neither commit is pushed.
- 2026-08-17: **engine schema 1.2.0 landed** — the engine can now say how many
  extra hours are still owed, not just how many were worked. Applied as the two
  commits decided on 2026-08-10: `9b8fdd1` the formatting sweep, `dca94c5` the
  change. The lock was lifted for a verified file copy of the five files parked
  in `notes/pending-engine-1.2.0/` and restored immediately after. New:
  `afc_hours/payments.py` (ingest + a pure `reconcile()` drawing paid minutes
  down against the weeks oldest-first), a per-month aggregation and invariant I7
  in `core.py`, and the `monthly` / `payments` blocks plus
  `totals.above_contract_minutes` in `emit.py`. Tests 116 + 29 green, up from
  67 + 29, with the one intended break being the schema tripwire re-pinned to
  1.2.0. Nothing published moved: added four keys, removed none, every
  pre-existing key unchanged — 26 343 min over 9 weeks to 31 July, 14 193 above
  contract, and with no payments file the block correctly reads paid 0, unpaid
  14 193, `paid_up_to: null`. Both copies of `web_data.json` are untouched at
  schema 1.1.0, so the live site is unchanged until `regen.sh` learns to pass a
  reconciliation.
  Three things worth keeping from doing it:
  (a) APPLY.md's formatting command was wrong in reach — it formats whole
  directories, six files and 667 lines, where the approved decision was three
  files and 458. Caught before committing by re-measuring with
  `ruff format --diff`; the extra three files are now a parked Later item.
  (b) `cp` is aliased to `cp -i` in this environment, so APPLY.md's plain `cp`
  would have silently skipped the three overwrites and left a half-applied
  engine with a puzzling test failure. `command cp -f`, then `diff -q` each file.
  (c) the emitted key is `above_contract_minutes`; APPLY.md's
  `Totals.above_contract_min` is the internal field name. The website reads the
  long form.
- 2026-08-10: designed the hours-OWED mechanism (planning only; no engine or
  website code touched). The gap: nothing anywhere records what payroll has
  settled, so neither HR nor Vince can tell how many extra hours are actually
  owed — only how many were worked. Answer: a Payments tab in the same
  workbook (one row per payment event), the engine subtracts, the site shows
  the remainder. Design decisions taken with the user: one owed bucket rather
  than per-band; a short week is zero extra, never negative (the log holds no
  leave data, so offsetting would invent a fact); one lock-lift carrying both
  the payments work and the monthly array. Written: `PLAN.md` (full success
  criteria) and `data/payments_template.csv` (header-only on purpose — a
  leftover example row would ingest as a fake payment). Two findings from
  reading the engine that shaped the design: (a) `core.compute()` takes rows
  only, which its docstring calls the structural guarantee that no flag can
  inflate the hours, so payments must live in a separate module rather than
  become an argument to it; (b) the money-free test only looks for `£`/`gbp`,
  so a free-text note saying `$400` or "salary arrears" would reach a public
  page unchallenged — ingest will reject a wider set than the test checks.
  Baseline recorded before any change: 96 tests green (67 engine, 29
  characterisation), no golden-hash pin anywhere, but
  `test_emit.py::test_schema_version_is_current` pins 1.1.0 deliberately and
  is meant to break on the bump.
- 2026-08-02: routine ingest through to 31 July (commit "31 of July
  finished") — two new working days (30 and 31 Jul) added to the canonical
  CSV from a 47-row export, with both copies of web_data.json regenerated in
  the same commit. First real use of the pipeline closed on 2026-07-29; it
  worked with no hand steps.
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
  engine, integrity clean, export named correctly, frozen sample data and engine
  code untouched). Never commits or pushes — prints the commands and stops.
  On a stop it says exactly what did and did not move. (e) `scripts/deploy.sh`
  added, replacing a stub: takes a commit message, re-checks that the served
  copy matches the engine and that the figures pass integrity, stages only the
  four data paths, reports anything it deliberately left out, commits, pushes,
  and says whether that actually deployed (only main does). Reached from
  anywhere via `~/.local/bin/nhs-log-deploy`; `nhs-log-injest` in the same
  folder points at ingest.sh.
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
  build passes, grep audit clean, three-scenario headless-browser check (real
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
  as six focused commits (data adoption + sample data, F1 test repoint, F2–F4
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
