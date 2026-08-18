# Plan: ingest the spreadsheet itself, both tabs, one download

**Goal:** download `filipe_working_hours_log.xlsx` and run one command. Both
tabs — hours and payments — reach the engine, and everything downstream of the
conversion behaves exactly as it does today.

STATUS: **APPROVED 2026-08-18 and in progress.** Steps 1 and 2 done; see the
worklog at the end.

Covers `docs/TODO.md` Now item 1's last piece (step 6b of the archived schema
1.2.0 plan, `notes/plans/2026-08-10_hours-owed.md` §5) and pulls forward the
headless xlsx→csv conversion listed under Now item 2 for `update.sh`.

---

## 0. What changed, and why this replaces the previous design

The first version of this plan had `ingest.sh` recognise two *families of CSV*
in the downloads folder and route each by its header. That was written on the
assumption that both tabs could be exported side by side.

They cannot: the spreadsheet exports one tab per CSV, but the whole workbook
downloads as one `.xlsx`. So the file to ingest is the workbook, and the
two-families routing problem disappears — a single file always carries both
tabs, and there is no second export left to forget.

This also removes the quiet failure that made 6b urgent in the first place:

> Today a payments export sitting in `~/downloads` is silently ignored.
> `find_source` only matches a header beginning `Date,Start,End,Minutes,Hours,`,
> so `nhs-log-ingest` reports success while the payment never reaches the
> engine.

With the workbook as the source there is nothing to miss. The urgency stands
for a different reason: until this lands, a payment recorded in the spreadsheet
cannot reach the site at all.

## 1. What is actually in the workbook

Read 2026-08-18 from the real file with `openpyxl`, not assumed.

Two sheets, `log` and `payments`, and nothing hidden.

| sheet | range | contents |
|---|---|---|
| `log` | `A1:F59` | header plus **58 rows**, ending **2026-08-18** |
| `payments` | `A1:D1` | header only, no rows |

`log`'s header is `Date, Start, End, Minutes, Hours, ' Main events in the day'`
— the leading space on the last column is real and is in the canonical CSV too.
`payments`' header is `Date, MinutesPaid, HoursPaid, Note`, matching
`data/payments_template.csv`.

**The published data stops at 31 July with 47 rows.** So this workbook carries
roughly eleven new working days, and ingesting it will move every headline
figure. That is a deliberate, separate step at the end of this plan, not a side
effect of building it.

`openpyxl` returns typed values rather than the raw XML, so conversion is
formatting rather than arithmetic:

| cell | stored as | openpyxl gives | CSV needs |
|---|---|---|---|
| `A2` | serial `46174` | `datetime(2026, 6, 1)` | `1-Jun-26` |
| `B2` | fraction `0.3645833…` | `time(8, 45)` | `08:45` |
| `C2` | fraction `0.7375…` | `time(17, 42)` | `17:42` |
| `D2` | `537` | `537` | `537` |
| `E2` | `8.9499999999999993` | `8.95` | `8.95` |

Checked against the canonical CSV's first row, which reads
`1-Jun-26,8:45,17:42,537,8.95,Induction + chat with mark + reading a lot of
material`. The workbook reproduces every value in it (the Start hour's padding
is the one formatting difference; the worklog explains why). The standard 1900 epoch is in
use; there is no `date1904` flag to handle.

`python-openpyxl` 3.1.5 is installed system-wide, inside the container and out,
by user decision 2026-08-18.

## 2. Approach

### 2.1 A converter that stands on its own: `scripts/xlsx_to_csv.py`

A separate file rather than a heredoc inside `ingest.sh`, unlike `probe` and
`drift_check`. It is big enough to be worth reading on its own, and being
runnable standalone is what makes criterion 1 a one-line check.

    python3 scripts/xlsx_to_csv.py <workbook.xlsx> <out-dir>

writes `<out-dir>/hours.csv` and `<out-dir>/payments.csv`, and prints a line per
sheet saying how many rows it wrote and what date each ends on.

Formatting rules, each pinned because a wrong one moves a figure or breaks the
byte-comparison that proves the converter:

- **Date** → `%-d-%b-%y`, giving `1-Jun-26`, no leading zero.
- **Start / End** → `HH:MM`, zero-padded, giving `08:45` and `17:42`. Settled
  by measurement, not taste — see the worklog on criterion 1.
- **Minutes** → the integer as-is.
- **Hours** → two decimal places, so the float that is really
  `8.9499999999999993` is written `8.95`.
- **Notes** → verbatim, with the `csv` module's own quoting, which is what
  produced the existing `"Tour with Vince through the department, chat…"`.
- **Header** → written verbatim, including the leading space in
  ` Main events in the day`.

Row rules:

- A row whose `Date` cell is empty is skipped. Spreadsheets carry trailing blank
  rows and they must not become empty CSV lines.
- A row with a `Date` but missing `Start`, `End` or `Minutes` is a hard error
  naming the row number. The engine would catch it a moment later, but the row
  number in the *spreadsheet* is what the user needs to fix it.
- Cell values are read by column letter, never by position, so a blank `Note`
  cannot shift the columns.

The converter computes nothing. It reads what the spreadsheet holds and writes
it in the shape the engine already accepts. Minutes are copied, not derived from
Start and End — the engine's own cross-check of the two is left to do its job.

### 2.2 Finding the workbook

`~/downloads` holds seven `.xlsx` files, so "the newest spreadsheet" is not
good enough. Discovery takes the newest `.xlsx` **whose sheet names include one
carrying the hours header** — matching by content, exactly as the CSV discovery
matches by header today rather than by filename.

An explicit path still works and may be either kind:

- `scripts/ingest.sh path/to/workbook.xlsx` — converted, then ingested.
- `scripts/ingest.sh path/to/export.csv` — routed by header to the hours or the
  payments path.

Keeping CSV input is not politeness to the old way: **criterion 2 depends on
it**, because re-ingesting an archived CSV export is how the hours path is
proved unchanged.

If no workbook is found, the error says so and says a CSV may be passed
explicitly.

### 2.3 Downstream is unchanged, and that is the point

After conversion the derived CSVs go through the pipeline exactly as a
downloaded CSV does today: probe, duplicate check, drift gate, archive,
canonical copy, one `regen.sh` at the end.

The engine keeps taking CSVs and stays locked — no lift, no re-audit, no change
to the frozen test fixture. `data/exports/` keeps holding CSVs, so the audit
trail stays diffable text. If the converter is ever wrong, it shows up as a CSV
diff before anything is published.

The payments side needs the three stages it has never had:

- **probe** — `payments.ingest_payments_csv` rather than
  `core.compute_from_csv`, printing `<last-payment-date> <rows> <total-minutes>`
  and dying with the engine's own row-numbered message. A zero-row file is legal
  and reports `none 0 0`.
- **drift** — the same three categories as hours (CHANGED, REMOVED,
  BACKFILLED) over date → sorted minutes. The note is deliberately excluded: it
  never reaches `web_data.json`, so an edited note moves no figure and must not
  stop an ingest.
- **archive** — `payments_export_<stamp>_covers-to-<last-payment-date>.csv`,
  its own prefix so the two families stay tellable apart, and
  `covers-to-none` when there are no rows.

The existing byte-identical duplicate check covers the case that would otherwise
be annoying: with the payments tab empty, every run derives the same header-only
CSV, and after the first archive it is recognised as already held rather than
copied again.

**Today's empty payments tab still writes `engine_v2/data/payments.csv`.** An
explicit empty ledger is clearer than an absent file, and the engine treats them
identically — `ingest_payments_csv` returns `[]` for both.

### 2.4 The safety property to preserve

An empty payments export must never quietly wipe recorded payments. If the
canonical file holds rows and a header-only export replaces it, every payment
vanishes and the owed figure jumps back up. This needs no special case: the
drift gate sees every row as REMOVED and stops. It is written into the
invariants so nobody later decides the gate is over-cautious.

### 2.5 `ingest-check.sh` and `deploy.sh`

- Newest-export check covers both families, and **guards the glob**:
  `data/exports/payments_export_*.csv` matches nothing until the first payments
  ingest, and under `set -euo pipefail` an unmatched glob makes `ls` fail and
  kills the script.
- Both re-parse `engine_v2/data/payments.csv` through the engine if it exists.
- Both gain paid, owed and paid-up-to in the printed summary, so the figures
  that changed are visible before publishing.
- `ingest-check.sh` gains a check that **no note text reaches the output** — a
  tripwire on the engine's structural guarantee, not a substitute for it.
- `deploy.sh` needs nothing for staging: `DATA_PATHS` already contains
  `engine_v2/data` and `data/exports`, verified by reading.

### 2.6 The stale count

`ingest-check.sh:70` and `deploy.sh:59` both print "all six integrity checks
true". `content.integrity` has carried **seven** `*_ok` keys since I7 landed
with schema 1.2.0. Their logic already reads every `*_ok` key it finds, so this
is one word each. `regen.sh` prints no count and needs nothing.

---

## Success criteria

Each is a command whose output settles it. Criteria 1 to 8 run against a
throwaway copy of the repo under the scratchpad, never the working one.

1. **The converter reproduces the engine's existing input exactly.** Convert the
   workbook, take the derived hours CSV's rows up to and including 2026-07-31,
   and compare against `engine_v2/data/filipe_working_hours_log.csv`. Every
   field must match, and the engine must compute **every day identically** from
   both files. Any change to a figure, a date, a time value or a note is a stop
   — it means the conversion is lossy, not that the data moved.

   *Revised 2026-08-18, after the first run failed and the reason turned out to
   be in the existing file rather than the converter — see the worklog.* The
   original wording was "byte-identical", which is not achievable: the canonical
   CSV pads the Start hour in 32 of its 47 rows and not in the other 15, so no
   single formatting rule reproduces it. The criterion is now equality of every
   field plus identical engine output, with hour padding named as the one
   permitted textual difference.
2. **The hours path is unchanged.** Re-ingesting
   `data/exports/hours_export_2026-08-02_1557_covers-to-2026-07-31.csv` — the
   export the current canonical CSV came from — into a fresh copy produces the
   same figures and the same drift report as today's script does on the same
   input. Captured before the change and compared after.
3. **The workbook ingests both tabs in one run.** One command converts, probes,
   archives both derived CSVs under their own prefixes, updates both canonical
   files, and runs `regen.sh` **once**.
4. **Bad payments input is refused before anything is copied.** Three cases,
   each stopping with the engine's own row-numbered message and leaving
   `engine_v2/data/payments.csv` untouched: `HoursPaid` contradicting
   `MinutesPaid`; a note containing a money word; two identical rows.
5. **Bad spreadsheet input is refused with the spreadsheet's row number.** A row
   with a date but no `Start` names the row as it appears in the sheet.
6. **The drift gate protects recorded payments.** Against a canonical
   `payments.csv` holding two rows: one row removed stops the run and prints
   REMOVED; a past payment's minutes changed stops and prints CHANGED;
   `--accept-drift` adopts either. A header-only export stops the same way
   rather than silently emptying the ledger.
7. **Nothing gates on payment warnings.** With an overpayment recorded,
   `ingest-check.sh` and `deploy.sh` both still report PASS and offer to
   publish, with the overpayment visible in the summary. `grep` confirms neither
   fail condition reads `content.payments.warnings`.
8. **No note text is published**, and **the count is right**: distinctive words
   from payment notes appear nowhere in `web_data.json`; `grep -n "six"
   scripts/` returns nothing; `shellcheck` passes on all four scripts.
9. **The real ingest, run deliberately and last.** On the working repo, ingest
   the actual workbook: the data extends from 47 rows ending 31 July to 58 rows
   ending 2026-08-18, the figures move accordingly, `nhs-log-deploy` publishes,
   and the live page is checked in a browser. **This changes what the public
   page says and is its own decision** — it is listed here so the plan is
   honest about ending in a publish, not so it happens automatically.

### Invariants — must never be violated

- **The hours path behaves exactly as it does today** for CSV input. Criterion
  2, and the one that matters most: it is the command run on a routine.
- **The converter never computes a figure.** It reformats what the spreadsheet
  holds. Minutes are copied, never recalculated from Start and End — the
  engine's cross-check of those two must keep meaning something.
- **No script ever fails on `content.payments.warnings`.** An overpayment is a
  true state of the world; gating on it would make the site permanently
  unpublishable the first time payroll settles more than was accrued.
- **The canonical payments CSV is never replaced without the drift gate having
  a chance to stop it**, including by a header-only export.
- **Nothing writes inside `engine_v2/afc_hours` or `engine_v2/tests`.** The
  existing checks in `ingest-check.sh` already assert both and stay.
- **The `.xlsx` is never committed.** User decision 2026-08-18: the repo is
  public, and the archive stays known, diffable text. The derived CSVs are what
  the engine consumed and are what answers "which input produced this figure".
- **A note never reaches `web_data.json`.** Structural in the engine already;
  criterion 8 is the tripwire.

## Explicitly out of scope

- **`scripts/update.sh` and the cron wrapper** — the rest of `docs/TODO.md` Now
  item 2. This plan makes the conversion exist; scheduling it is separate, and
  committing and pushing stays deliberately manual because the push publishes.
- **Any engine change.** `engine_v2/` stays locked; no lift needed.
- **Any website change.** The page already renders everything a payment
  produces, checked across six scenarios on 2026-08-18.
- **Reading anything but the two known sheets.** A third tab appearing later is
  ignored, not guessed at.
- **The colleague names already public in the hours CSV.** Real, pre-existing,
  needs its own decision.

## Risks and rollback

| risk | mitigation |
|---|---|
| The conversion is subtly lossy — a rounded minute, a mangled note | Criterion 1 is a byte-comparison against the file the engine already consumes, over 47 rows of real data. Nothing subtle survives that. |
| The refactor breaks the hours ingest | Criterion 2 compares before-and-after output on a real export in a throwaway copy. |
| An empty payments tab wipes recorded payments | Criterion 6 and its invariant; the drift gate sees every row as REMOVED. |
| Ingesting the workbook publishes eleven new days before anyone has looked | Criterion 9 is deliberately last, deliberately on the working repo, and deliberately needs its own decision. `ingest-check.sh` still stops and prints the command rather than publishing. |
| Testing dirties the real repo or the locked engine | Criteria 1 to 8 run against a copy under the scratchpad; `git status` checked clean afterwards. |

**Rollback:** the scripts are plain files in git with no migrations and no
external state — `git checkout -- scripts/` restores them. Criteria 1 to 8
publish nothing. Criterion 9 is a normal data commit and reverts like any other.

## Order of work

1. [ ] Copy the repo to the scratchpad. Capture today's hours-ingest output on
       the 2026-08-02 export as the baseline for criterion 2.
2. [ ] `scripts/xlsx_to_csv.py`, then criterion 1 — the byte-comparison against
       the canonical CSV. Nothing else starts until that passes.
3. [ ] `ingest.sh`: workbook discovery, the conversion stage, the payments
       probe, drift comparator and archive, help text.
4. [ ] Criterion 2 against the baseline. Any difference is a stop.
5. [ ] Criteria 3 to 6 against the copy, with hand-built payments CSVs and a
       hand-broken workbook.
6. [ ] `ingest-check.sh` and `deploy.sh`: payments checks, summary lines, glob
       guard, count wording. Criteria 7 and 8.
7. [ ] Commit. One for the converter, one for `ingest.sh`, one for the two
       checking scripts — separable, and the risk sits in the middle one.
8. [ ] `docs/TODO.md`: Done entry; Now item 2 loses its conversion half.
9. [ ] **Stop and ask** before criterion 9, the real ingest and publish.
10. [ ] Archive this plan to `notes/plans/` once the criteria are evidenced.

### Worklog

**Step 1 — baseline captured.** Repo cloned to the scratchpad; re-ingesting
`hours_export_2026-08-02_1557_covers-to-2026-07-31.csv` gives 47 rows, 26 343
min, latest 2026-07-31, no historical drift, all seven `*_ok` keys true. That is
the output criterion 2 compares against.

**Step 2 — `scripts/xlsx_to_csv.py` written, criterion 1 passed on the second
attempt. The first attempt failed and the fault was in the existing data, not
the converter.**

The workbook's 58 rows converted cleanly, but comparing the first 47 against the
canonical CSV showed 32 rows differing. Measured rather than eyeballed: the only
differing field was `Start`, and normalising the hour padding made the two files
identical. **The canonical CSV is internally inconsistent** — it writes `8:45`
in 15 rows and `08:00` in 32, almost certainly because it was assembled from
exports taken at different times. No single rule can reproduce it byte for byte,
which is why the criterion was revised rather than the converter bent to fit.

Proven before deciding anything: the engine computes 26 343 min, 47 days, 9
weeks, identical bands and classes, and `[(date, start_min, end_min)]` identical
for every day from both forms. The padding is invisible to it.

The converter therefore zero-pads (`08:45`). That matches the larger group, so
the one-time cosmetic reformat is **12 rows** rather than 32 — 12 and not 15
because rows starting at 10:00 or later are unaffected either way. From here on
the converter is the only thing that writes this file, so it stays consistent.
The 12 cosmetic rows will sit in the same commit as 11 genuinely new days, and
the commit message has to say so plainly.

Two things found while reading the real workbook, both now guarded in the
converter:

- **`Minutes` and `Hours` are formula cells** — 116 of them, two per row.
  `openpyxl(data_only=True)` returns the value the spreadsheet last calculated,
  so a workbook written by something that does not evaluate formulas would
  arrive with those cells empty. That is a hard error naming the sheet row, not
  a blank passed through.
- **No `End` hour is single-digit** anywhere in the canonical file or the 58 new
  rows, so padding `End` changes nothing today and is safe to apply uniformly.

**Steps 3 to 6 — done, criteria 2 to 8 all evidenced.**

- **Criterion 2 (the hours path is unchanged) — PASS.** Re-ingesting the
  2026-08-02 export through the new script gives output differing from the
  baseline in exactly two lines, both deliberate relabelling: "validated" became
  "hours validated" and "canonical CSV updated" became "canonical hours CSV
  updated", so the two paths can be told apart. Every figure, the drift report,
  the archive decision and the whole `regen.sh` block are identical. One
  unintended regression was caught by this comparison and fixed: the
  `source: <path>` line had disappeared for CSV input.
- **Criterion 3 (both tabs, one run) — PASS.** With the real workbook and a
  deliberately *newer* unrelated spreadsheet in the same folder, discovery picked
  the right file by content and ignored the decoy. 58 rows, 32 055 min, latest
  2026-08-18, **no historical drift, +11 rows**; both derived CSVs archived under
  their own prefixes; both canonical files updated; `regen.sh` ran once. Three
  months now, and all seven `*_ok` keys true.
- **Criterion 4 (bad payments refused) — PASS**, all three with the engine's own
  row-numbered message and `payments.csv` untouched each time: `HoursPaid 99.00`
  against `MinutesPaid 3000`; a note reading "salary arrears"; two identical
  rows.
- **Criterion 5 (bad spreadsheet rows) — PASS.** A blanked `Start` gives
  `sheet 'log' row 7: Start is None, which is not a time`; a blanked `Minutes`
  gives `row 9: Minutes is empty (a formula that was never calculated?)`. Both
  name the row as it appears in the spreadsheet, which is where the fix happens.
- **Criterion 6 (the drift gate protects payments) — PASS.** Against a canonical
  holding two payments: a removed row prints REMOVED and stops, a changed amount
  prints `CHANGED 2026-07-15: 3000 min -> 9999 min` and stops, and a header-only
  export prints REMOVED for *both* rows and stops — the wipe this invariant
  exists for. `--accept-drift` adopts. Canonical untouched in every refusing
  case.
- **Criterion 7 (nothing gates on payment warnings) — PASS.** With 23 000 min
  paid against 16 210 accrued, `ingest-check.sh` prints the overpayment and the
  engine's warning and still reports ALL CHECKS PASSED, offering the publish
  command; `deploy.sh` likewise reaches "staged for this commit". Both fail
  conditions read `ig['warnings']` — integrity — and nothing else.
- **Criterion 8 — PASS.** Payment notes ("July claim") appear nowhere in
  `web_data.json`, checked by the new tripwire. `shellcheck` clean on all four
  scripts. The hard-coded "six" is gone from both scripts, replaced by
  `len(oks)` so it can never go stale again rather than being re-pinned to
  seven.

Two things worth keeping:

- **The latent crash was real.** `ingest-check.sh` globbed
  `data/exports/hours_export_*.csv` through a pipe under `set -euo pipefail`;
  adding a payments glob naively would have killed the script on the first run,
  before any payments export existed. Both globs are now guarded.
- **`[[ cond ]] && cmd` as a standalone statement is a `set -e` trap** — when
  the test fails the list returns 1 and the script exits. It would have made a
  payments-only ingest abort silently. Written as full `if` statements, with the
  reason in a comment so it does not get "tidied" back.
