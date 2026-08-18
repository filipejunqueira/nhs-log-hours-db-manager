# Plan: track hours OWED, not just hours worked (schema 1.2.0)

**Goal:** anyone reading the site — Vince, HR, payroll — can answer *"how many
extra hours is he owed, and since when?"* without asking. Today the site shows
hours **accrued**; nothing anywhere records hours **settled**, so "owed" cannot
be computed by anyone.

**The whole idea in one line:**

    owed = extra hours accrued − extra hours paid

The engine already knows the first term. This plan adds the second and does the
subtraction in the engine, where every hours figure belongs.

STATUS: APPROVED and PART-DONE, five commits deep and **unpushed**. The engine
landed 2026-08-17 (steps 1-5), and `regen.sh` (step 6a) and website 1.4.0
(step 7a) landed the same day. The engine lock was lifted for the file copy and
is back on.

**What is left, and nothing else:** step **7b, the rendered-page check** — the
one criterion still unevidenced, specified in §7 — and then step **8, the
push**. The payments-aware `ingest.sh` / `ingest-check.sh` / `deploy.sh`
(step 6b) is deliberately deferred *past* the push; the deviation and the risk
it accepts are set out in "Decisions 2026-08-18".

Nothing published has moved. Both copies of `web_data.json` are at schema 1.2.0
in git, but `main` is five commits ahead of `origin`, so the live page still
serves the 1.1.0 data and shows no owed figure.

Covers **`docs/TODO.md` Now item 1** in full. Does not touch Now item 2
(`scripts/update.sh`).

Decided with the user 2026-08-10:
- one owed bucket (all minutes above contract), not split by band or class;
- a short week is zero extra, never negative — the log holds no leave data, so
  offsetting would invent a fact;
- **option (a)**: one engine lock-lift carries *both* the payments work and the
  per-month breakdown, so the audited engine is opened and re-verified once;
- input is a new **Payments tab** in the same workbook (template written:
  `data/payments_template.csv`).

---

## 0. What blocks the start

`engine_v2/**` is deny-listed for Edit and Write in `.claude/settings.json`.
Steps 2–4 below cannot begin until the user removes those two lines. That is the
deliberate lock-lift; it goes back on before the work is committed, exactly as it
did on 2026-07-19. Steps 1, 5 and 7 need no lift.

---

## 1. Input: the Payments tab

New tab in the existing workbook, exported to `engine_v2/data/payments.csv`.
Header, matching the template already written:

    Date,MinutesPaid,HoursPaid,Note

| column | meaning |
|---|---|
| `Date` | the day the payment landed (or the payslip date — be consistent) |
| `MinutesPaid` | authoritative, a positive whole number |
| `HoursPaid` | minutes ÷ 60; a redundancy cross-check — but a mismatch here is a hard error, not a warning as in the hours log (§2 says why) |
| `Note` | free text for humans — "July claim, payslip Aug" |

**One row per payment event, not a single "paid up to" date.** Payroll does not
always settle in tidy blocks; a ledger copes with partial payments, and — the
part that matters — an *underpayment stays visible* as a persistent remainder
instead of silently disappearing.

**Payments settle the oldest unpaid week first.** That keeps the input dead
simple: no deciding which weeks a payment covers. Even if payroll's own
attribution differs, the headline — total owed — is unaffected by the ordering.

**Today's state is zero payments, and it must be a first-class case.** No file
at all, or a header-only file, is legal and means `paid = 0`, `owed =
everything accrued`. `core.compute()` raises on empty input; the payments ingest
must *not* copy that.

### `Note` stays in the spreadsheet — it is not emitted

`RawDay`'s docstring in `core.py` reads "one validated worked period from the
CSV (**notes dropped**)": the hours log's free-text column has never reached
`web_data.json`. Looking at what that column actually holds — *"chat with
mark"*, *"Tour with Vince through the department"* — the reason is plain, and
it is the identity-light cardinal rule. A payment note is no different, so
**`note` is not emitted**. The ledger shows date, hours and running total,
which is everything a reader needs to check the arithmetic.

That also shrinks the money guard rather than growing it: with the note never
leaving the spreadsheet, no free text can put a pay figure on the page. Ingest
still rejects a note containing a currency symbol (`£ $ € ¥`) or a whole-token
match against the engine's money-token list (`salary gbp wage rate rates
multiplier pension premium cost money gross net`), because — see the warning
below — the CSV itself is committed.

> **Separate, pre-existing exposure, worth a decision of its own:** the repo is
> **public** (decision of 2026-07-19), and `deploy.sh` commits
> `engine_v2/data/`. So `filipe_working_hours_log.csv` — colleague names and
> all — is *already* readable by anyone, regardless of what the JSON omits.
> Dropping `note` from the emitted JSON keeps the new work consistent with
> existing practice; it does **not** fix that. Flag to the user; do not quietly
> fold a change of that size into this plan.

---

## 2. Engine: the payments side (new module)

`core.compute(rows)` takes rows only — its docstring calls this "the structural
guarantee that no flag inflates the hours". **Payments must not become an
argument to it.** They go in a separate module:

**`engine_v2/afc_hours/payments.py`** (new)

- `ingest_payments_csv(path) -> list[Payment]` — missing file returns `[]`.
  Dates parse via the same formats as the hours log but **without** the
  bank-holiday-year restriction: payments run into future years.
- `reconcile(weeks, payments) -> Reconciliation` — a pure function.

Reconciliation walks the weeks in date order, drawing down a pool of paid
minutes:

    extra(week)   = minutes_by_band[additional] + minutes_by_band[overtime]
    unpaid_minutes = max(0, Σ extra − Σ paid)
    overpaid_minutes = max(0, Σ paid − Σ extra)

`paid_up_to` needs pinning down, because the obvious definition — "Sunday of
the last fully-settled week" — quietly misfires on a week with no extra hours:
such a week is trivially settled, so with zero payments the panel could
announce a paid-up-to date beside `paid_minutes: 0`, reading as though a
payment happened. (Checked against the real log 2026-08-10: all nine weeks
currently have extra > 0 — the smallest is W28 at 40 min — so today the naive
definition happens to behave; the pin is a guard, not a fix for a live bug.)
The definition, covering every case:

    paid_up_to = null   whenever paid_minutes == 0,
                        and also when no week with extra > 0
                        is yet fully settled;
                 otherwise the Sunday of the last fully-settled
                 week that has extra > 0.

**Two different kinds of "wrong" get two different treatments:**

- `HoursPaid` disagreeing with `MinutesPaid` is a **hard ingest error**, not a
  warning. This deliberately differs from the hours log, where a Minutes
  mismatch only warns — there, Start/End recompute the true value, so the
  mismatch is resolvable. A payment row has no second source: one of the two
  numbers is mistyped and nothing can say which, so publishing either would be
  guessing at an owed figure. Refuse, name the row, stop.
- **Overpayment is a warning, never an error** — it is a true state of the
  world (or a sign the log is behind), not a data-entry contradiction, and the
  page must be able to publish it.

## 3. Engine: the per-month breakdown

`core.py` gains a `months` field on `HoursResult`, aggregated from the atomic
segments by calendar month — `month`, `day_count`, `total_min`,
`minutes_by_band`, `minutes_by_class`, mirroring the weekly summary.

**Months do not re-band.** Bands are a property of the Monday-to-Sunday pay-week
and stay that way; a month simply sums minutes already banded by their week. So
a week straddling 31 July contributes minutes to both months carrying the bands
its *week* assigned. This is subtle enough to belong in the emitted methodology,
not just here.

## 4. Engine: emitted shape (schema 1.2.0)

`emit.py`: `SCHEMA_VERSION` → `"1.2.0"`, `build_payload` gains a
`reconciliation` keyword (defaulting to a reconciliation against an empty
payment list, so the block is always present and always truthful).

    content.totals.above_contract_minutes      # NEW: additional + overtime

    content.monthly: [                          # NEW
      { "month": "2026-06", "day_count": 21, "total_minutes": 11020,
        "minutes_by_band": {...}, "minutes_by_class": {...} } ]

    content.payments: {                         # NEW
      "paid_minutes": 0, "unpaid_minutes": 3520, "overpaid_minutes": 0,
      "paid_up_to": null,
      "ledger": [ { "date": ..., "minutes_paid": ...,
                    "cumulative_paid_minutes": ... } ],   # no note — see §1
      "unpaid_weeks": [ { "iso_week": ..., "monday": ...,
                          "unpaid_minutes": ... } ],
      "warnings": [] }

**Payment warnings live in `content.payments.warnings` and must NEVER be
routed into `content.integrity.warnings`.** This is load-bearing, not tidiness:
`regen.sh`, `ingest-check.sh` and `deploy.sh` all refuse to publish while
`integrity.warnings` is non-empty (verified in all three, 2026-08-10). Funnel
an overpayment warning in there and the first real overpayment makes the site
permanently unpublishable — the exact failure the "warn, never refuse" decision
exists to prevent. Integrity warnings stay what they are today: hours-data
problems that a spreadsheet fix resolves.

`above_contract_minutes` lives in `totals` **only** — it is a pure function of
the hours and needs no payment data. It is also the figure the header already
shows via `sumMinutes` in the browser, so emitting it here delivers the parked
2026-07-19 decision and lets `sumMinutes` be deleted.

Every new key checked against the money-token list: none collide.

### New methodology lines

- monthly banding, as described in §3;
- payments settle the oldest unsettled week first; the total owed does not
  depend on that ordering;
- **`unsocial_within_baseline_minutes` is inside the contracted 22.5 hours and
  is therefore NOT part of the owed figure.** Someone reading an "owed" panel
  could easily assume it means everything claimable. Say so in the file.

### New invariants

- **I7 monthly conservation** — monthly totals sum to `totals.total_minutes`,
  band by band and class by class. Lives in `core._check_invariants`, surfaces
  as `integrity.monthly_ok` (which `regen.sh` and the integrity panel both pick
  up automatically, since they read every `*_ok` key).
- **I8 reconciliation** — `above_contract_minutes == additional + overtime`, and
  `paid − overpaid + unpaid == above_contract`, and the per-week unpaid figures
  sum to `unpaid_minutes`. Asserted inside `reconcile`.

---

## 5. Scripts

**Status: `regen.sh` is DONE (2026-08-17, commit `f36e2a3`). The other three are
step 6b, deferred past the push — see "Decisions 2026-08-18".**

- **`regen.sh`** — pass `data/payments.csv` (if present) to the engine; add
  paid/unpaid/owed to the printed check block. Keep the build-into-`.tmp`
  discipline exactly as it is. Its fail condition stays `integrity.warnings`
  only — payment warnings print but do not block (see §4).
- **`ingest.sh`** — more than "a second header branch": the payments path forks
  **all four stages**, because `probe()` and `drift_check()` both run the
  *hours* engine on the file (read 2026-08-10) and would reject a payments CSV
  outright.
  - *detect*: route each file by header — `Date,Start,End,Minutes,Hours,` →
    hours, `Date,MinutesPaid,HoursPaid,Note` → payments. Today a payments
    export in `~/downloads` is silently ignored.
  - *probe*: payments files validate through `payments.ingest_payments_csv`,
    not `core.compute_from_csv`.
  - *archive*: own family, `payments_export_<stamp>_covers-to-<last-payment-date>.csv`
    — same collision-proof pattern, distinct prefix so the two families are
    tellable apart in `data/exports/`.
  - *drift*: own comparator (date → paid-minutes list); the hours comparator
    compares start/end periods, which payments do not have.
  - *canonical copy*: to `engine_v2/data/payments.csv`, then `regen.sh` as now.
- **`ingest-check.sh`** — **currently absent from this plan's thinking; it has
  two checks the new work trips.** Its newest-export check globs
  `hours_export_*.csv` only, so a payments export would dodge the naming check
  entirely; and its "no engine warnings" check is one of the three gates that
  must keep reading `integrity.warnings` only. Add: payments-export naming
  check, a paid/unpaid summary line, and the payments file re-parsed.
- **`deploy.sh`** — `DATA_PATHS` already contains `engine_v2/data` and
  `data/exports` (verified 2026-08-10), so the payments CSV and its archives
  are staged for free. Add a pre-publish check that the payments file, if
  present, still parses.
- All three checking scripts print "all six integrity checks true" — the word
  "six" goes stale when I7 lands. Their *logic* survives untouched (each reads
  every `*_ok` key it finds), so this is one word per script, but say "seven"
  or drop the count.

## 6. Website (app version 1.4.0)

**Status: DONE (2026-08-17, commit `d1e0984`) — every bullet below is in the
code. What remains is not in this list: the rendered-page check, now §7.**

The schema gate accepts any 1.x with minor ≥ 1, so 1.2.0 passes with no change
to `schema.ts`.

- **`validate.ts`** — do **not** add `payments`/`monthly` to `REQUIRED_BLOCKS`.
  That list is the fatal list, and this file's own decision is that a future
  engine release must never be able to take the live page down. Missing new
  block → hide that panel, add a warning.
- **`OwedPanel.vue`** (new), directly under the header — the five-second read:
  *"Extra hours not yet paid: 68 h 20 m"*, with *paid up to w/e …* and the last
  payment beneath. With zero payments it shows everything accrued as owed, so it
  is useful from day one.
- **`PaymentsTable.vue`** (new) — date, hours, running total. No note column;
  the note never leaves the spreadsheet (§1).
- **`MonthlyTable.vue`** (new) — mirrors `WeeklyTable`.
- **`format.ts`** — delete `sumMinutes`; the header reads
  `totals.above_contract_minutes` instead. `validate.ts` gains a
  warning-level check for that key: absent (a 1.1.x file) → hide the header
  figure behind the amber banner rather than render "NaN h". Site and data
  deploy from the same commit, so this is belt-and-braces, but it costs three
  lines and fits the file's existing philosophy.
- `types/web-data.ts`, `App.vue` wiring, `package.json` → 1.4.0.

Still hours only. Nothing new is published that the page did not already show —
it already shows extra hours; this adds "of which unpaid".

---

## 7. The rendered-page check (step 7b — the next thing)

Criterion 7's last clause: *does the number on the page equal the number in the
JSON?* Every other part of criterion 7 is evidenced. This is not.

### Why it earns the effort rather than being waved through

Verified 2026-08-18 by reading the code and the data, not inferred:

- The live payments block reads `paid_minutes: 0`, `ledger: []`,
  `overpaid_minutes: 0`, `paid_up_to: null`. So **every conditional in the owed
  display has only ever rendered its zero arm** — `paid_up_to ?? 'nothing
  settled yet'`, the `paid_minutes === 0` ternary, `v-if="overpaid_minutes > 0"`,
  and `PaymentsTable.vue:38`'s `v-for="e in payments.ledger"`, which has never
  produced a single row.
- `regen.sh:38` calls `payments.ingest_payments_csv('data/payments.csv')`
  against a file that does not exist — `engine_v2/data/` holds only the hours
  CSV. The reconciliation path has never run end to end outside the Python
  tests.
- **A suspicion tested and killed, recorded so it is not re-suspected:**
  `OwedPanel.vue` could have been reading `above_contract_minutes` where it
  should read `unpaid_minutes` — identical today, divergent the moment payroll
  pays anything. It is not. Line 26 binds `payments.unpaid_minutes`, correctly.

### The six scenarios

A scenario is a copy of `web_data.json` standing for one situation, served from
`website/dist/` while the rendered page is read back.

| scenario | how it is made | what it proves |
|---|---|---|
| `real` | today's `web_data.json`, untouched | normal render, no amber banner, 236.55 h owed |
| `partial` | engine output for two payment rows summing to **5 400 min** | the subtraction reaches the page — paid 90.00 h, owed 146.55 h, accrued 236.55 h, a real `paid_up_to`, a part-settled week, and a ledger table with rows in it |
| `overpaid` | engine output for one row of **15 000 min** | `overpaid_minutes` 807, owed floors at zero, and the `v-if` block nothing has ever rendered |
| `no-payments` | `real` with `content.payments` deleted | the owed panel disappears entirely; amber banner |
| `no-above-contract` | `real` with `totals.above_contract_minutes` deleted | the header shows a dash, not `NaN h` |
| `no-monthly` | `real` with `content.monthly` deleted | the monthly table copes |

The last three stand in for a `web_data.json` from the 1.1.0 engine: still
perfectly renderable, simply unable to say what is owed.

**Two things settled 2026-08-18 so step 7b does not trip over its own spec:**

- **Payment dates cannot disturb any figure.** `reconcile()` sets
  `pool = paid_total` and walks *all* weeks oldest-first applying
  `min(pool, extra)` (`payments.py:262-271`). The dates are used only to order
  the ledger and build `cumulative_paid_min`. So the pinned July and August
  dates are free choices and cannot move `paid_up_to 2026-06-21` — only the
  5 400 total decides it.
- **The `overpaid` scenario must expect NO amber banner.** `validate.ts` builds
  its warnings solely from missing blocks and unrecognised band/class keys; it
  never reads `content.payments.warnings` or `integrity.warnings`, so the
  top-of-page banner does not fire on an overpayment. The reader is told all
  the same, twice, inside the owed panel: `OwedPanel.vue:62-66` renders its own
  sentence when `overpaid_minutes > 0`, and the list beneath it prints the
  engine's warning text verbatim. Both confirmed rendering 2026-08-18. Leave it
  that way — do not wire payment warnings into the top banner, for the same
  reason the three scripts must never gate on them.

**The partial and overpaid figures come from the engine, never from hand-editing
the JSON.** Writing "paid 5 400, unpaid 8 793" by hand would check the page
against a number I invented, which is exactly the circularity the cardinal rule
exists to prevent.

**5 400 is not arbitrary.** It reproduces the end-to-end case already
hand-checked in the sandbox worklog below: owed 8 793 min, `paid_up_to
2026-06-21`, W26 part-settled with 1 819 remaining, FIFO clearing W23+W24+W25
exactly. `reconcile()` derives `paid_up_to` from the **weeks**, not from the
payment dates (`payments.py:277-287` walks the settlements, stops at the first
week still owing, and takes the Sunday of the last fully-settled week that had
extra hours), so *any* split summing to 5 400 reproduces all three figures.
Pinned anyway, so the ledger rows are deterministic:
`2026-07-15, 3000, 50.00` and `2026-08-14, 2400, 40.00`.

That gives the scenario a second job: if the landed engine does not reproduce the
sandbox's numbers, the sandbox and the shipped engine have drifted. That is a
stop-and-report, not a re-pin.

### Rules for building them

- **Nothing writes inside `engine_v2/`.** Build the scenarios by calling the
  engine in Python and writing the JSON to the scratchpad — the same way step 5
  built its payload in memory. Do **not** drop a temporary `payments.csv` into
  `engine_v2/data/` and run `regen.sh`: that writes into the locked directory,
  dirties both copies of `web_data.json` with a fresh `generated_at`, and risks
  leaving a fake payment behind.
- Running `regen.sh` against a real payments file *is* worth doing — it is the
  last untested link in the chain — but as its own deliberate step with its own
  cleanup, not folded into 7b.

### Prerequisites — all verified 2026-08-18, none outstanding

- `playwright` 1.62.1 present in `website/node_modules`.
- Chromium **revision 1234** is what 1.62.1 asks for, and it is cached at
  `.cache/ms-playwright/chromium-1234`. `chromium.launch()` succeeds and reports
  browser version 151.0.7922.34. No `npx playwright install` needed.
- All seven strings `check-render.mjs` matches on still exist in the components:
  `owed-heading`, `payments-heading`, `monthly-heading`, `Hours above contract`,
  `does not fully understand`, `Could not load`, `p.text-4xl`.

### The script itself

`website/scripts/check-render.mjs` exists, uncommitted, and **has never been
executed once**. Its scenario path points at a dead `/tmp` scratchpad belonging
to the session that wrote it, wiped when the laptop lost power on 2026-08-17.
Treat its first green run as evidence about the script as much as about the
page — in particular, its weeks-owing selector takes `.last()` of the tables
under `payments-heading`, which assumes the ledger table is the first of two,
and that is only true once the ledger has rows.

---

## Success criteria

1. **Zero payments works** — no `payments.csv` at all, and a header-only one,
   both produce `paid_minutes: 0`, `unpaid == above_contract_minutes`, an empty
   ledger, **`paid_up_to: null`**, and a rendering owed panel. *This is the only
   state that exists today, so it is criterion 1.*
2. **The arithmetic** — on hand-built cases covering no payments / partial /
   exact / overpaid: `unpaid == max(0, accrued − paid)` in every case;
   overpayment warns rather than failing; a row whose `HoursPaid` contradicts
   `MinutesPaid` is refused at ingest with the row named.
3. **Tests** — 96 green (67 engine + 29 characterisation) with **exactly one
   deliberate change**: `test_emit.py::test_schema_version_is_current`, re-pinned
   from 1.1.0 to 1.2.0. That test is a tripwire and is *meant* to break on a
   schema bump. Any other test that goes red is a real regression, not
   bookkeeping. New tests added for payments ingest, reconciliation, monthly
   conservation and the note guard.
4. **Existing figures do not move** — every pre-existing key in `content` is
   byte-identical before and after, on the real log. The diff is additions
   only. Baseline recorded 2026-08-10: **26 343 min over nine weeks, period
   ending 31 Jul**. (The engine tests pin 16 808 min against the *frozen
   sample* `hours_2026-07-14.csv`, not the live log — verified; those pins
   are untouched by this work.)
5. **Nothing free-text is published** — no entry in `content.payments.ledger`
   carries a `note` key (checked by script, **not** by `grep -i note` on the
   whole file: `meta.unit_note` already exists and would false-positive),
   matching how the hours log's notes are already dropped; and a note
   containing `£`, `$`, `€` or any money word is rejected at ingest with a
   message naming the word.
6. **Ingest and deploy** — a payments export in `~/downloads` is detected,
   archived without collision, and drift-checked; `deploy.sh` stages it; the
   hours path is completely unaffected. **Deferred past the push (step 6b).**
   It is not a precondition for publishing figures that are already computed;
   it becomes required the moment a first payment is recorded. The consequence
   knowingly accepted until then is §5's own words — *"today a payments export
   in `~/downloads` is silently ignored"*.
7. **Website** — `vue-tsc -b` clean (**not** `npx vue-tsc --noEmit`, which
   checks zero files here), build passes, `sumMinutes` gone from the codebase
   (invariant I9): **all three done, commit `d1e0984`.** Outstanding: a
   headless-browser check of the owed panel against the raw JSON, on the **six**
   scenarios specified in §7 — not the three named here on 2026-08-10, which
   were written before it was known what the components would branch on.
   *Prerequisite resolved 2026-08-18:* Playwright is a devDependency and its
   Chromium is cached and launches; see "Decisions 2026-08-18".
8. **The reader test** — someone who has never seen the repo can answer "how
   many extra hours is he owed, and since when?" from the page alone.

### Invariants — must never be violated, encoded as assertions

These are conditions, not outcomes. Each is asserted in code, so a future change
that breaks one fails loudly rather than quietly publishing a wrong figure.

- **I1–I6 keep holding, unchanged.** The six existing invariants are not
  weakened, reworded or made conditional. Adding blocks must not touch them.
- **I7 monthly conservation** — Σ monthly `total_minutes` == `totals.total_minutes`,
  and the same band by band and class by class. (In `core._check_invariants`,
  surfacing as `integrity.monthly_ok`.)
- **I8 reconciliation** —
  `above_contract_minutes == minutes_by_band[additional] + minutes_by_band[overtime]`;
  `paid − overpaid + unpaid == above_contract_minutes`;
  and Σ `unpaid_weeks[].unpaid_minutes` == `unpaid_minutes`.
  (Asserted inside `reconcile`.)
- **I9 no figure is invented in the browser.** After this work `format.ts`
  contains no arithmetic beyond minutes ÷ 60, clock formatting — `sumMinutes` is
  gone. Checkable by grep, as the existing grep audit already does.
- **Owed is never negative.** Overpayment shows as `overpaid_minutes`, and
  `unpaid_minutes` floors at zero. A short week contributes zero extra, never a
  negative offset.
- **The engine stays the only source of hours figures.** No band, class or total
  is computed in TypeScript.

## Explicitly out of scope

- **Money, rates, and `money.py` (Part ii).** This is hours-owed, not
  pay-owed. Nothing in this plan emits or displays a monetary amount.
- **The public-repo exposure of colleague names** in the existing hours-log CSV
  (flagged in §1). Real, pre-existing, and needs its own decision — not folded
  in here.
- **`scripts/update.sh`** — TODO.md Now item 2, untouched.
- **The unverified "unit-tested 11 cases" claim** in the 2026-07-19 Done log,
  still parked by your earlier decision.
- **A totals row on CrossTab** — still deliberately minimal.
- Any change to how hours are *classified or banded*. Bands, classes and the
  22.5-hour rule are untouched; this plan only aggregates and subtracts.

## Risks and rollback

| risk | mitigation |
|---|---|
| The lock-lift leaves `engine_v2/` unprotected and something unrelated gets edited | Lift immediately before step 3, restore immediately after step 4 — the same discipline as 2026-07-19. `git diff` reviewed before the deny rules go back. |
| Existing figures shift silently under the new aggregation | Criterion 4 is byte-identical pre-existing keys. Any movement is a stop-and-report, not a re-pin. |
| A rejected regen leaves the two `web_data.json` copies disagreeing | Already solved — `regen.sh` builds into `.tmp` and renames only on success. Do not weaken that while adding the payments argument. |
| The schema bump breaks the live page | The gate accepts any 1.x with minor ≥ 1, verified by reading `schema.ts`. New blocks are non-fatal in `validate.ts` by design. |
| Publishing wrong owed figures to people who act on them | Criteria 1, 2 and invariant I8. Nothing is pushed until the whole criteria list is evidenced. |

**Rollback:** every step is a normal git revert — no migrations, no external
state. The engine change is additive, so reverting to schema 1.1.0 output
restores the current site exactly. The one irreversible act is *publishing* an
owed figure to a public page; that is why the criteria are checked before the
push, not after.

## Order of work

1. [x] Housekeeping — archive the executed plan, TODO.md Done entry. *(no lock)*
2. [x] **Engine work built and proven in a throwaway copy** at
       `scratchpad/sb-engine`, the same pattern used on 2026-07-29. Criteria
       1–5 all evidenced there; see the worklog below. Doing this first means
       the lock is open for a verified file copy, not for development.
3. [x] **User lifted the engine lock** 2026-08-17.
4. [x] Applied as **two commits** (user decision 2026-08-10, see below):
       `9b8fdd1` the ruff-format sweep, `dca94c5` schema 1.2.0 on top.
5. [x] Figures verified unmoved and **the lock is back on**. The regeneration
       named here was deliberately NOT done: `regen.sh` cannot run against the
       new engine until it passes a reconciliation, so it belongs to step 6.
       Verified instead by building the payload in memory from the real log and
       comparing it key for key against the committed `web_data.json` — see the
       worklog below. *(Superseded the same day: `f36e2a3` regenerated both
       copies at 1.2.0. The live site is still unchanged — the commits are
       unpushed.)*
6. [x] **6a — `regen.sh` passes a reconciliation.** Commit `f36e2a3`. Both
       copies of `web_data.json` regenerated at schema 1.2.0; 236.55 h owed.
7. [x] **7a — website 1.4.0.** Commit `d1e0984`. `OwedPanel`, `PaymentsTable`,
       `MonthlyTable`, `sumMinutes` deleted, `validate.ts` warnings added.
8. [x] **7b — the rendered-page check. DONE 2026-08-18, all 87 checks pass**
       (worklog at the end). Specified in §7. In order:
       1. Answer the one open question in "Decisions 2026-08-18": where the
          scenario files live. Everything after this depends on it.
       2. Build the six scenarios — three by deleting one block from today's
          `web_data.json`, two from engine output for the pinned payment rows,
          one the real file untouched. Nothing writes inside `engine_v2/`.
       3. Check the `partial` scenario reproduces the sandbox's recorded figures:
          owed 8 793 min, `paid_up_to 2026-06-21`, W26 with 1 819 remaining. A
          mismatch means sandbox and shipped engine have drifted — stop and
          report, do not re-pin.
       4. Repoint `check-render.mjs` at wherever the scenarios now live (its
          current path is a dead `/tmp` directory) and add the `partial` and
          `overpaid` assertions: paid, owed and accrued read as three different
          numbers on the page, the ledger table has rows, the overpaid block
          renders, and owed never goes negative.
       5. Run it against `vite preview` on port 4177. Record PASS/FAIL per
          scenario in the worklog below.
9. [x] **8 — PUSHED AND CONFIRMED LIVE 2026-08-18.** Three commits:
       `4fc3036` the check machinery and the six scenarios, `b261a15` these
       plan and TODO updates, `992b9dd` website 1.4.1 fixing what the check
       found. The public page now reads **236.55 h owed** — verified in a
       headless browser against the deployed URL, not just by fetching the
       JSON: owed panel present, headline 236.55 h, "nothing settled yet",
       header tile 236.55, two monthly rows, no amber banner, no page
       errors.
10. [ ] **6b — payments-aware `ingest.sh`, `ingest-check.sh` and `deploy.sh`**
       (§5). **THIS IS NOW THE NEXT THING.** Deferred past the push; required
       before the first payment is recorded. Carries the stale wording too: all three scripts say "all six
       integrity checks true" and `integrity` has had **seven** `*_ok` keys
       since I7 landed. One word each; their logic is unaffected.
11. [ ] Archive this plan to `notes/plans/2026-08-10_hours-owed.md` once 6b
       lands, per the project's own convention.

### Decisions 2026-08-18 — one deviation and three smaller calls

**1. The push is re-gated on criterion 7 alone. This deviates from step 8 as
originally written**, and is recorded rather than done quietly.

Step 8 said push after criteria 6 *and* 7. That was written on 2026-08-10,
before the payments work split into an engine piece and a scripts piece landing
weeks apart. Holding back a verified page for scripts that handle a file which
does not yet exist is the wrong trade: criterion 6 governs the *next* ingest,
not whether what is being published now is correct.

**The risk this knowingly accepts**, in §5's own words: *"today a payments
export in `~/downloads` is silently ignored."* Silently is the word that
matters. Between the push and 6b landing, if a payments export is downloaded and
`nhs-log-ingest` run, it reports success, the file is never archived, never
reaches `engine_v2/data/payments.csv`, and the page keeps showing the full
amount as owed. Nothing fails loudly. That is tolerable only while no payment
has been received — today's state — so **6b must land before the first payment
is recorded**. The trigger is that event, not a date.

**2. Playwright stays a devDependency.** This plan offered two options
(criterion 7, deferred from 2026-07-21); the working tree took this one and it
is confirmed. The throwaway install has evaporated twice now and cost a
session's work both times. Measured cost, not assumed: version 1.62.1 has no npm
install script (`hasInstallScript: false` in the lockfile, empty `scripts` in
the installed package), so CI's `npm ci` does **not** download browsers and the
Pages deploy is unaffected — a few MB more and nothing else.

**3. Fixture-building must not run `regen.sh` against a temporary
`payments.csv`.** Reasons in §7. The end-to-end run is worth doing on its own
terms; it is not part of 7b.

**4. RESOLVED — the scenario files are COMMITTED**, under
`website/scripts/scenarios/`. Six files, 196 KB. The alternative was generating
them at run time from the current `web_data.json`, which keeps the repo lighter
and can never drift from the current shape.

What decided it: **step 7b.3's cross-check only holds while the data is the nine
weeks to 31 July.** A generated `partial` would pay the same 5 400 minutes
against a *larger* accrued total after the next ingest, so owed would come out
different and the paid-up-to date could land on another week. The check would
fail with nothing actually wrong, and read as engine drift — the wrong
conclusion at the worst moment. Committed files keep that cross-check valid
indefinitely.

Two supporting reasons. The check now tests only the website: it needs no Python
and no working engine, so an engine problem cannot break it. And committed files
age *loudly* — at the next schema bump the `real` scenario starts raising the
amber banner and trips its own "no banner" expectation, forcing a look, where a
generator would quietly rebuild from the new shape and keep passing while
covering less. That is the same reasoning as
`test_emit.py::test_schema_version_is_current`, which is pinned precisely so it
breaks on a bump.

Noted, since `docs/TODO.md` Later says no test framework in `website/` unasked:
six data files and one Node script is not vitest. That is a reading, not an
assumption — flagged to the user when the choice was put.

### Decision 2026-08-10: formatting is its own commit

The engine was **never ruff-formatted** — it uses deliberate hand-aligned
comments (`DAYTIME = "daytime"        # weekday 06:00-20:00`). The global ruff
hook reformats it on any write, which would add **458 cosmetic lines** to an
audited file next to the **239 substantive** ones, burying the real change and
breaking the audit report's line references with no record of why.

Measured, not estimated: formatting churn is core 294 / emit 94 / test_emit 70;
the 1.2.0 change is core 66 / emit 97 / test_emit 76. Proven behaviour-neutral
before offering the choice: the format-only copy passes all 96 tests and emits
**byte-identical** JSON.

User chose two commits, formatting first. Never mix them.

### Worklog — evidence gathered in the sandbox

- **Criterion 1 (zero payments)** — PASS. No file and header-only both give
  `paid 0`, `unpaid == above_contract == 14 193`, empty ledger,
  `paid_up_to: null`.
- **Criterion 2 (arithmetic)** — PASS. Parametrised over paid ∈ {0, 1, 600,
  1999, 2000, 2001, 99999}: I8 balances at every amount. Overpayment warns.
  An `HoursPaid` contradicting `MinutesPaid` is refused with the row named.
- **Criterion 3 (tests)** — PASS, exactly as predicted. Before adding new
  tests: **1 failed, 66 passed**, the failure being
  `test_schema_version_is_current` — the deliberate tripwire — and all 29
  characterisation tests green and untouched. After re-pinning and adding
  `test_payments.py`: **145 green** (116 engine + 29 characterisation).
- **Criterion 4 (nothing moved)** — PASS. Added `content.monthly`,
  `content.payments`, `totals.above_contract_minutes`,
  `integrity.monthly_ok`; removed nothing; **every pre-existing key
  byte-identical**. Real-log baseline 26 343 min, 9 weeks, to 31 Jul.
- **Criterion 5 (no free text published)** — PASS. `LedgerEntry` has no note
  field at all, so a note cannot be serialised even by mistake; asserted via
  `__dataclass_fields__` and by checking the note string is absent from the
  whole JSON.
- **End-to-end** — two payments totalling 5 400 min against 14 193 accrued
  gave owed 8 793 min (146.6 h), `paid_up_to 2026-06-21`, and W26 part-settled
  at 1 819 remaining. Hand-checked: FIFO clears W23+W24+W25 exactly and 90 min
  into W26. 5 400 + 8 793 = 14 193.

Discovered while building, worth keeping:
- `_check_invariants` needed a new `months` parameter — it is positional and
  called from one place, so the signature change is contained.
- The ruff hook deletes an import added in an earlier tool call than its first
  usage (F401 auto-fix). `emit.py`'s `payments` import was silently removed and
  had to be re-added once the usage landed. Documented in the global rules;
  hit it anyway.
- `"pay"` was deliberately dropped from the money-word list: "back pay",
  "pay run" and "payslip Aug" are the natural way to write a note and state no
  amount. The guard exists to keep figures out of a public file, not to police
  vocabulary.

### Applied 2026-08-17 — steps 3 to 5

Two commits, as decided: `9b8fdd1` formatting, `dca94c5` schema 1.2.0.

**Correction to the formatting decision — it was measured on three files, not
the directory.** The 458 lines recorded above are core 294 + emit 94 +
test_emit 70, which is exactly the three files 1.2.0 changes. But APPLY.md's
command was `ruff format engine_v2/afc_hours/ engine_v2/tests/`, whole
directories, which reformats **six** files for **667** lines — it also hits
`rules.py` (50), `test_core.py` (98) and `test_rules.py` (56), the three files
APPLY.md itself lists as untouched. The extra churn on `rules.py` is exactly
the hand-aligned-comment collapse this two-commit split exists to keep visible,
and `rules.py` is the rules-as-law file the audit report's line references point
at. Measured under ruff 0.15.20; `emit.py` and `test_emit.py` match the August
counts to the line, so this is not version drift — the sandbox simply never
measured the other three.

**User decision 2026-08-17: format only the three files** 1.2.0 touches. That
is what was approved, and the parked files were built to sit on exactly that
base. Formatting the other three is deferred to its own job (now in
`docs/TODO.md` Later). Known consequence: the global ruff hook will reformat
`rules.py` the first time anything writes to it.

**Evidence gathered on the real repo, not the sandbox:**

- Formatting is behaviour-neutral: 67 + 29 green afterwards, and the payload
  built in memory from the real log is identical to the committed
  `web_data.json` key for key, `generated_at` aside.
- All five parked files landed byte-identical (`diff -q` on each). Note `cp` is
  aliased to `cp -i` here, which would have silently skipped the three
  overwrites — `command cp -f` is required.
- Today's ruff wants no change to the five parked files, so none of their
  formatting leaked into the 1.2.0 commit.
- Tests **116 engine + 29 characterisation**, exactly as predicted.
- Criterion 4 holds on the real log: added `content.monthly`,
  `content.payments`, `totals.above_contract_minutes`, `integrity.monthly_ok`;
  removed nothing; **every pre-existing key unchanged**. 26 343 min over 9 weeks
  to 31 July, 14 193 above contract. Zero payments gives paid 0, unpaid 14 193,
  `paid_up_to: null`, empty ledger, no payment warnings.

**Two facts step 6 and 7 need:**

- The emitted key is **`above_contract_minutes`**. APPLY.md's table says
  `Totals.above_contract_min`, which is the internal dataclass field — the JSON
  key is the long form, and that is what `format.ts` must read.
- `content.integrity` now carries **seven** `*_ok` keys (`monthly_ok` is new).
  The "all six integrity checks true" wording in `regen.sh`, `ingest-check.sh`
  and `deploy.sh` is now stale, as §5 anticipated. Their logic is fine — each
  reads every `*_ok` key it finds.

### Landed 2026-08-17 — steps 6a and 7a

Two further commits the same day the engine landed. Neither is published: `main`
is five commits ahead of `origin`.

- **`f36e2a3` — `regen.sh` reconciles.** It reads
  `engine_v2/data/payments.csv`, reconciles against the weeks, and hands the
  result to `emit.write_json`. Payments are read *in the script* and passed to
  `emit`, never into `core.compute()`, which takes rows only — its own docstring
  calls that the structural guarantee that no flag can inflate the hours. A
  missing payments file stays legal. The printed check block gained
  above-contract, the month list, paid, owed, paid-up-to and payment warnings;
  the fail condition still reads `integrity.warnings` **only**, so an
  overpayment prints but never blocks publishing. Both copies of `web_data.json`
  regenerated at 1.2.0 and byte-identical (sha `4b1401a1`); against the previous
  committed JSON the only changes are the four added keys, three methodology
  lines, the schema version and `generated_at`. Also deleted
  `notes/pending-engine-1.2.0/`, which APPLY.md asks for at this step.
- **`d1e0984` — website 1.4.0.** `OwedPanel`, `PaymentsTable`, `MonthlyTable`.
  `sumMinutes` deleted, which **discharges invariant I9** — `format.ts` now
  holds nothing but minutes ÷ 60 and clock formatting, and the header reads the
  engine's `totals.above_contract_minutes` instead of adding up. `validate.ts`
  gained warning-level checks for a missing `payments` block, a missing
  `monthly` block and a missing `totals.above_contract_minutes`;
  `REQUIRED_BLOCKS` is deliberately untouched, so a pre-1.2.0 file still
  renders — it simply cannot say what is owed. Verified: `vue-tsc -b` clean,
  production build passes, grep confirms no arithmetic outside `format.ts`, and
  the built site serves 1.2.0 over `vite preview` showing **236.55 h owed**.

### Still unevidenced after those two commits

Criterion 7's rendered-page check, and only that. It is now §7 and step 7b.

### Ran 2026-08-18 — step 7b, the rendered-page check

**Result: 87 checks across six scenarios, ALL PASS.** `website/scripts/` now
holds `check-render.mjs` and `scenarios/` with the six committed files.

**The builder validates itself before building anything.** It first emits a
control payload with no payments and compares it against the committed
`engine_v2/web_data.json`: **identical**. So the in-memory build reproduces what
`regen.sh` produced, and any scenario built the same way can be trusted. Nothing
was written inside `engine_v2/` — the engine was called in Python, the payments
CSVs were written to the scratchpad, and `git status` shows the engine untouched.

**The `partial` scenario reproduces the sandbox exactly** — the cross-check step
7b.3 asked for, and it passes on every figure: paid 5 400, unpaid 8 793,
`paid_up_to 2026-06-21`, W26 with 1 819 still owing, 2 ledger rows. So the
engine that shipped and the engine proven in the sandbox on 2026-08-10 agree.

**What the payment scenarios showed on the page**, which nothing had ever
rendered before:

- `partial` — accrued 236.55 h, paid 90.00 h, owed 146.55 h read as three
  different numbers, the ledger table produced its first ever rows, "settled up
  to" printed a real date instead of "nothing settled yet", and the last-payment
  cell matched the final ledger row.
- `overpaid` — 15 000 min paid against 14 193 accrued: the owed headline floors
  at `0.00 h`, the overpayment block renders 13.45 h, and the engine's warning
  text appears verbatim in the list beneath it. No top-of-page amber banner, as
  §7 predicted.

**A selector bug in `check-render.mjs`, found and fixed before the run.** It
took `.last()` of the tables under `payments-heading` to count weeks owing. That
holds while a ledger table is present, but the `overpaid` scenario has a ledger
and *no* weeks owing — so the ledger table becomes the last one and its single
row would have been counted as a week still owing. Both tables are now anchored
on their own column headings (`Running total`, `Still owing`). This is exactly
the "the first green run is evidence about the script too" caveat in §7, and it
earned its keep.

**One real finding, NOT fixed — the user's call whether it belongs in this
push.** In the `no-above-contract` scenario the page contradicts itself:
the header tile correctly shows a dash, but `OwedPanel.vue:30` reads
`data.content.totals.above_contract_minutes ?? 0` and so prints *"Of the 0.00 h
worked above the contracted 22.50 h a week, 0.00 h have been settled so far"*
directly beneath a headline saying **236.55 h** are owed. The `?? 0` fallback
invents a zero where `SummaryHeader.vue:38` shows a dash; the two handle the
same missing key differently. The one-line fix is to mirror the dash. Severity
is low — it needs a pre-1.2.0 JSON served to a 1.4.0 site, and site and data
deploy from the same commit, so this is the belt-and-braces case the plan
already describes — but the sentence states something false, and the amber
banner explains the dash rather than the sentence.

Worth recording about the check itself: it derives every expectation from the
scenario's own JSON, **including that `?? 0`**, which is why it passed the case
above rather than catching it. A page-versus-JSON check agrees with the
component wherever the component invents a fallback. Reading the output still
found it.

### Pushed 2026-08-18 — step 8, and one fix the check earned

`main` pushed to `origin`; GitHub Actions built and deployed. **Schema 1.2.0 is
live and the page says 236.55 h are owed.** Confirmed twice: the deployed
`web_data.json` reads schema 1.2.0 with `above_contract_minutes` 14 193 and the
two monthly rows, and a headless browser pointed at the live URL found the owed
panel rendering 236.55 h with no page errors and no amber banner.

**The one thing the rendered-page check found is fixed and shipped**
(`992b9dd`, website 1.4.1). `OwedPanel.vue` read `above_contract_minutes ?? 0`
where `SummaryHeader.vue` shows a dash, so a pre-1.2.0 file rendered "Of the
0.00 h worked above the contracted 22.50 h a week" beneath a headline saying
236.55 h were owed. Both now show a dash. Belt-and-braces rather than a live
bug — data and site deploy from the same commit, so it was unreachable in
production — but the sentence stated something false.

Worth keeping, because it says what this kind of check is *for*: the assertion
did not catch it. `check-render.mjs` derived its expectation with the same
`?? 0` the component used, so it agreed with the component and passed. **A
page-versus-JSON check agrees with the component wherever the component invents
a fallback.** Reading the output caught it. The assertion now pins the dash, so
it would catch it next time.

**What is left of this plan:** step 6b only, plus archiving the plan itself.
Everything the site publishes today is evidenced.
