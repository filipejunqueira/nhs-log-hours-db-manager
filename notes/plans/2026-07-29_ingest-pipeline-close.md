# Plan: close the ingest pipeline gaps (naming, website copy)

**Goal:** a spreadsheet export reaches the live site without a hand-copy anyone
can forget, and every ingested CSV is kept forever under a name that cannot
collide.

STATUS: EXECUTED 2026-07-29 — all three changes made; every success criterion
and all six invariants checked against a throwaway copy of the repo, then one
confirming run on the real one. The previous plan (code-review follow-ups) is
archived at notes/plans/2026-07-28_code-review-followups.md; this one archives
at the next session wrap-up.

Results, against a sandbox copy at scratchpad/sb1 unless stated:

- [x] **Criterion 1 + 6 (regen standalone)** — `regen.sh` leaves the website
      copy byte-identical every run. Verified on the sandbox and on the real
      repo.
- [x] **Criterion 2** — ingest.sh inherits it and prints
      "OK: copied to website/public/web_data.json".
- [x] **Criterion 3** — a clean ingest wrote
      `hours_export_2026-07-29_1034_covers-to-2026-07-16.csv`.
- [x] **Criterion 3, the collision case** — two *different* exports both ending
      14 Jul were archived side by side (`..._1035_...` and `..._103539_...`,
      the second via the seconds fallback). The old scheme would have named both
      `hours_export_2026-07-14.csv` and overwritten one.
- [x] **Criterion 4** — re-ingesting the identical file reported
      "already archived: byte-identical to …" and created no second copy.
- [x] **Criterion 5** — drift run flagged `CHANGED 2026-06-01` plus two
      `REMOVED` days, exited 1, and left both the export folder and the
      canonical CSV untouched. `--accept-drift` proceeded as before.
- [x] **Criterion 6 (shellcheck)** — clean on both scripts. The write hook
      caught one genuine half-finished edit during the work (`target`
      referenced but no longer assigned) and blocked it.
- [x] **Invariant 1** — same CSV, identical `content` and `meta` blocks before
      and after, on the sandbox *and* the real repo. 16 808 min unchanged. The
      real-repo run was then reverted with `git checkout`, since only
      `generated_at` had moved and the data files should not churn.
- [x] **Invariant 2** — export count only ever grew across every scenario
      (2 → 5). Nothing overwritten, nothing deleted.
- [x] **Invariant 3** — see criterion 5.
- [x] **Invariant 4** — a sentinel file left at
      `website/public/web_data.json` survived a deliberately failed integrity
      run untouched. Proved twice: once by forcing the failure, once by
      accident when a sloppy test fixture triggered the engine's own
      `Minutes differs from recomputed` warning.
- [x] **Invariant 5** — no engine change; `engine_v2/` is denied in
      .claude/settings.json and nothing under it was edited.
- [x] **Invariant 6** — `diff -rq` shows the sandbox `engine_v2/tests` tree
      identical to the real one; the frozen fixture was never touched.

Deviation from the plan: none in substance. `--force-export` was removed as
planned and exits 1 with the explanatory message.

Follow-on, agreed with the user after the plan was executed and outside its
original scope: `regen.sh` wrote `web_data.json` and validated it afterwards,
so a rejected run left the working tree holding refused data with the two
copies disagreeing. It now builds into `web_data.json.tmp` and renames it into
place only after the checks pass; a trap removes the temporary file on any
exit. This strengthens invariant 4 from "bad data never reaches the *published*
file" to "bad data never reaches *either* file". Verified: a run rejected for a
`Minutes` typo leaves both copies at an identical checksum, no leftover
temporary file, and an empty `git status`.

Also renamed: `plan.md` → `PLAN.md` via `git mv`, to match CLAUDE.md and the
plan-gate convention. Flagged to the user at approval time.

**Covers part of docs/TODO.md Now item 2** (`scripts/update.sh`): specifically
the "copy to website/public" link of that chain, plus the export-archive
weakness found while walking the pipeline. It does NOT write `update.sh` itself
— see Out of scope. Now item 1 (website improvements) is untouched.

Note: this file was `plan.md` (lowercase) until 2026-07-29, renamed via
`git mv` to match CLAUDE.md and the plan-gate convention.

## Context

Two gaps came out of walking through how a new spreadsheet export reaches the
live site.

**The website copy is not in the pipeline.** `scripts/regen.sh` writes
`engine_v2/web_data.json` and stops. The website reads its own copy at
`website/public/web_data.json`, and nothing copies one to the other. This is a
leftover: regen.sh was written on 26 June, before `website/` existed, and its
own closing comment lists the copy as deferred "once website/ exists". The
website was built on 19 July and nobody went back. Today the two files happen
to match (checked), but nothing keeps them that way, and a mismatch produces no
error anywhere — the engine would be current while the published page showed
old figures.

**The export archive is weaker than it looks.** Every ingested CSV is copied to
`data/exports/` and committed, which is good. But the filename is the latest
*work date found inside the file*, not when the export was taken. Two exports
downloaded weeks apart collide if no new working days were added, and the
documented answer to a collision is `--force-export`, which overwrites the
earlier file — so the folder stops being a complete record and the history is
only recoverable from git. The two files that exist do not even follow that
rule: `hours_export_2026-07-18.csv` contains data ending 14 July (confirmed by
running the engine on it), because both were named by hand, by download date,
before ingest.sh existed. The naming has already silently changed once.

Wanted: the published page can never quietly disagree with the engine, and
`data/exports/` holds one file per ingestion that is never overwritten.

Explicitly staying manual: `git add` / `commit` / `push`. Pushing publishes to
a world-readable page, so a bad export must not become public before a human
looks at it. That stays a deliberate step even when `scripts/update.sh` is
eventually written.

## Success criteria

1. Running `scripts/regen.sh` leaves `website/public/web_data.json` byte-identical
   to `engine_v2/web_data.json`, every time, without a separate command.
2. `scripts/ingest.sh` gets this for free (it calls regen.sh) and says so in its
   output.
3. A new ingestion writes `data/exports/hours_export_<ingest-time>_covers-to-<last-work-date>.csv`.
   Two ingestions can never produce the same name, so no export is ever
   overwritten.
4. Re-running ingest on a byte-identical file does NOT create a second copy — it
   reports which existing export it matches and carries on.
5. The drift check still stops on changed, removed or backfilled historical rows,
   exactly as now.
6. Both scripts pass shellcheck (the PostToolUse hook blocks the write otherwise).

## Invariants — must never be violated

Checked as part of the sandbox runs, not assumed:

1. **No published figure changes.** The same canonical CSV must produce
   byte-identical `web_data.json` content before and after this work. This is
   plumbing; it must not move a single minute.
2. **No file in `data/exports/` is ever overwritten or deleted** by ingest.sh.
   That is the whole point of the change.
3. **The drift check is never weakened.** A changed, removed or backfilled
   historical row still stops the run unless `--accept-drift` is passed.
4. **`website/public/web_data.json` is never written from failed data.** The
   copy sits after the integrity block, which already exits non-zero, so bad
   figures cannot reach the published file.
5. **`engine_v2/` is not modified** — locked, and denied in .claude/settings.json.
6. **The frozen test fixture under `engine_v2/tests/fixtures/` is not touched.**
   ingest.sh already states this; it stays true.

## Out of scope

- **`scripts/update.sh` itself.** This plan removes the manual copy that
  update.sh would otherwise have to perform; the wrapper stays unwritten.
- **Automating `git add` / `commit` / `push`.** Deliberate: pushing publishes to
  a world-readable page, so a human looks first.
- **Renaming the two existing exports.** They are committed and named in the
  Done log. A README records the two naming eras instead.
- **Headless xlsx to CSV** (BUILD_NOTES §5). Exporting stays a manual step.
- **The `meta.subject` check in regen.sh.** Offered separately, not taken.
- **Any engine change**, and any change to a figure the engine produces.

## Risks and rollback

- **Worst case: ingest.sh copies a bad CSV over the canonical one.** It already
  does this; the change does not touch that path, but testing happens against a
  throwaway copy of the repo regardless. Rollback is
  `git checkout -- engine_v2/data/filipe_working_hours_log.csv`, since the
  canonical CSV is committed.
- **regen.sh writing a bad website copy** is prevented by ordering, not by
  hope — the copy is unreachable if the integrity block exits first. Invariant 4
  tests exactly that.
- **Both scripts are committed**, so any change here is one `git checkout` from
  reverted. Nothing in this plan is destructive to data.

## Changes

### 1. `scripts/regen.sh` — copy to the website after a successful regen

Add after the integrity block (which already exits non-zero on failure, so the
copy only runs on good data):

```bash
WEB_PUBLIC="$REPO_ROOT/website/public/web_data.json"
if [[ -d "$(dirname "$WEB_PUBLIC")" ]]; then
    cp -f "$ENGINE/web_data.json" "$WEB_PUBLIC"
    echo "OK: copied to website/public/web_data.json"
else
    echo "NOTE: website/public not found; skipped the website copy" >&2
fi
```

This goes in regen.sh rather than ingest.sh on purpose: regen.sh is the thing
that produces `web_data.json`, so anyone running it directly also gets the
website in step. ingest.sh calls regen.sh, so it inherits the behaviour.

Delete line 2 of regen.sh's trailing "deferred" comment, which this implements.

### 2. `scripts/ingest.sh` — name exports so they cannot collide

Replace the naming at line 128. Current:

```bash
local target="$EXPORTS/hours_export_${latest}.csv"
```

New shape:

```
hours_export_2026-07-29_2043_covers-to-2026-07-14.csv
```

Sorted alphabetically, that is also sorted by ingestion time. The timestamp is
when the file entered the repo — the auditable event is "when did this become
the basis for published figures", and in practice you ingest right after
exporting.

Before writing, compare the source against every file already in
`data/exports/`. If any is byte-identical, report "already ingested as <name>"
and skip creating a duplicate, then carry on to the drift check and regen as
today. This keeps the useful half of the current collision handling.

`--force-export` is removed: nothing can collide any more. Keep an explicit
case for the flag that exits with "no longer needed — export names now include
the ingestion time, so nothing is ever overwritten", rather than the generic
"unknown flag", so an old habit gets a useful message.

`--accept-drift` is unchanged. The drift check is untouched.

### 3. `data/exports/README.md` (new)

Short note recording that the two 19-July files are named by download date under
the old hand-naming, that everything from 2026-07-29 onward is named by
ingestion time, and that no file in this folder is ever overwritten. Prevents
the next person concluding the archive is inconsistent by accident.

The two existing files are NOT renamed — they are committed and referenced in
the Done log, and churning history to fix cosmetics is not worth it.

## Verification

`ingest.sh` is the guard on your data, so it gets tested against a throwaway
copy of the repo in the scratch directory, never against the real one. Copy the
repo, point the script at fake export files, and check each scenario:

1. **Clean ingest of a genuinely newer export** — new file appears with the new
   name, canonical CSV updated, web_data.json regenerated, and
   `website/public/web_data.json` matches it byte for byte.
2. **Re-ingest the identical file** — reports "already ingested as …", creates no
   second copy, still ends with the two web_data.json files matching.
3. **Export with a changed historical row** — drift check still stops the run and
   prints the changed dates; nothing is written.
4. **Same drift with `--accept-drift`** — proceeds, as now.
5. **`--force-export`** — exits with the "no longer needed" message.
6. **regen.sh run on its own** — website copy updated without ingest.sh involved.
7. **`shellcheck scripts/ingest.sh scripts/regen.sh`** — clean. (The write hook
   enforces this anyway; a rejected edit is that hook, not a tool fault.)

Then, on the real repo: run `scripts/regen.sh` once with the current CSV and
confirm the figures are unchanged (16 808 min, 32 days, schema 1.1.0) and both
web_data.json copies match. No push — this changes no published figure, so it
rides along with the next real data update.
