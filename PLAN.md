# Plan: track hours OWED, not just hours worked (schema 1.2.0)

**Goal:** anyone reading the site — Vince, HR, payroll — can answer *"how many
extra hours is he owed, and since when?"* without asking. Today the site shows
hours **accrued**; nothing anywhere records hours **settled**, so "owed" cannot
be computed by anyone.

**The whole idea in one line:**

    owed = extra hours accrued − extra hours paid

The engine already knows the first term. This plan adds the second and does the
subtraction in the engine, where every hours figure belongs.

STATUS: AWAITING APPROVAL (`/plan-gate` opened 2026-08-10). Nothing implemented.

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

## Success criteria

1. **Zero payments works** — no `payments.csv` at all, and a header-only one,
   both produce `paid_minutes: 0`, `unpaid == above_contract_minutes`, an empty
   ledger, **`paid_up_to: null`**, and a rendering owed panel. *This is the only
   state that exists today, so it is criterion 1.*
2. **The arithmetic** — on hand-built fixtures covering no payments / partial /
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
   fixture* `hours_2026-07-14.csv`, not the live log — verified; those pins
   are untouched by this work.)
5. **Nothing free-text is published** — no entry in `content.payments.ledger`
   carries a `note` key (checked by script, **not** by `grep -i note` on the
   whole file: `meta.unit_note` already exists and would false-positive),
   matching how the hours log's notes are already dropped; and a note
   containing `£`, `$`, `€` or any money word is rejected at ingest with a
   message naming the word.
6. **Ingest and deploy** — a payments export in `~/downloads` is detected,
   archived without collision, and drift-checked; `deploy.sh` stages it; the
   hours path is completely unaffected.
7. **Website** — `vue-tsc -b` clean (**not** `npx vue-tsc --noEmit`, which
   checks zero files here), build passes, `sumMinutes` gone from the codebase,
   and a headless-browser check of the owed panel against the raw JSON on three
   fixtures: zero payments, partial payment, missing `payments` block.
   *Prerequisite:* Playwright's previous install was a throwaway in a dead job
   directory; the system libraries persist but the npm side must be redone.
   Either repeat the scratch install, or — **user decision, deferred from
   2026-07-21** — make Playwright a proper devDependency this time.
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
3. [ ] **User lifts the engine lock** (remove the two `engine_v2/**` deny
       lines from `.claude/settings.json`). ← THE ONLY BLOCKER
4. [ ] Apply as **two commits** (user decision 2026-08-10, see below):
       first the pure ruff-format sweep, then 1.2.0 on top.
5. [ ] Regenerate, re-verify figures unmoved, **user restores the lock**.
6. [ ] Scripts → criterion 6. *(no lock, but depends on the engine landing —
       `regen.sh` passing a reconciliation to an engine that cannot accept one
       breaks immediately, so these cannot go first)*
7. [ ] Website → criterion 7. *(same dependency)*
8. [ ] Commit, push, user confirms live.

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
