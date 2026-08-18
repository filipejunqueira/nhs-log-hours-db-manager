# Plan: full review — spreadsheet, engine, website, documents, all in agreement

**Goal:** establish, with evidence, that every figure a reader can encounter —
on the public page, in `web_data.json`, in the compiled audit document, and in
this repo's own records — is the correct consequence of what the spreadsheet
holds. Or, where one is not, say so precisely.

STATUS: **COMPLETE 2026-08-19.** All nine phases run; report at
`notes/reviews/2026-08-19_full-review.md`. Verdict: no finding changes any
published figure; three minor documentation findings, fixes proposed and
awaiting approval.

Requested 2026-08-18 after the audit document compiled: review everything —
engine, figures, website, documentation — and confirm it all agrees with the
spreadsheet.

---

## 0. The principle the whole review stands on

Re-running the engine's own tests is not a review — those tests passing is
already known, and a shared bug passes its own tests. The value of a review
comes from **independence**: deriving the same figures by a route that shares no
code with the engine, and comparing at every joint of the chain.

The chain under review, with a comparison at every arrow:

    workbook (.xlsx)  →  derived CSVs  →  engine  →  web_data.json (2 copies)
                                                            →  live page (JSON)
                                                            →  live page (DOM)
                                                            →  the .tex document
                                                            →  docs/ claims

The centrepiece is a **fresh reimplementation of the counting rules** in one
scratch script that never imports from `afc_hours` and is written from the rules
*as stated in prose* (the audit document and `AUDIT_BRIEF.md`), not from reading
`core.py`. Two implementations agreeing on 58 days × every category is strong
evidence; one implementation agreeing with itself is none. Where the two
disagree, the discrepancy is reported — not resolved by peeking at the engine
and "fixing" the reviewer to match.

Honest limits of that independence, stated up front: the same person is writing
both sides, the bank-holiday dates come from the same table, and a shared
misreading of AfC itself (e.g. whether the pay-week truly starts Monday) is
invisible to any internal check — which is exactly why the .tex asks payroll to
confirm the pay-week rather than claiming it.

## 1. Phase 0 — pin the ground truth

Nothing is reviewable until it is known *what* is being reviewed.

- The workbook: is `~/downloads/filipe_working_hours_log.xlsx` still what was
  ingested at 20:07 today? Convert it fresh and diff against both canonical
  CSVs. If the user has logged more hours since, the review proceeds against
  the *ingested* state and says so — it reviews what is published, not what is
  pending.
- `git status` clean; `main` in sync with `origin`.
- The two committed copies of `web_data.json` byte-identical, and the live
  page's JSON byte-identical to them.
- Record the exact commit hash the review ran against.

## 2. Phase A — the spreadsheet against itself

The source can be internally inconsistent in ways downstream agreement would
faithfully propagate. Row-level checks over all 58 rows, report-only:

- every End after its Start; no zero-length periods;
- `Minutes` equals End − Start exactly, row by row (the engine tolerates and
  warns; the review wants to know if any row relies on that tolerance —
  the engine reports zero warnings today, which this re-checks independently);
- `Hours` equals `Minutes`/60 to the recorded precision;
- no duplicate or overlapping periods on a date;
- dates in range, weekday named by the date checked against the calendar;
- plausibility: days over 12 h listed (there are some — 24 Jun is 757 min),
  not as errors but so the review has looked at them.

## 3. Phase B — the independent re-derivation (the centrepiece)

One scratch script, stdlib only, **no import from `afc_hours`**, reading the
workbook directly with openpyxl. It reimplements, from the prose rules:

- Monday–Sunday pay-weeks; minutes accumulated in chronological order;
- banding at 1350/2250 with mid-period splits at the exact minute;
- weekday clock classes split at 06:00/20:00; Saturday, Sunday and
  bank-holiday as whole-day classes; bank-holiday precedence;
- the within-baseline rule (unsocial minutes falling before the week's
  1350th);
- above-contract = additional + overtime; monthly aggregation; the
  cumulative series.

It then compares against `web_data.json`, figure by figure: grand total, all
three bands, all five classes, above-contract, within-baseline (the 225 — and
the script must also *name which day and minutes* produce it, because a figure
whose origin can be pointed at is worth more than one that merely matches),
all 12 weekly rows with their per-week bands, all 3 monthly rows, day count,
and the last cumulative value.

Also re-derived by the reviewer and shown as tables in the report, the way the
July audit did: every weekly total hand-summed from the row minutes, with two
weeks worked through in full detail (one plain week and the week containing
Sunday 16 August).

**Every mismatch is a finding.** None is resolved by adjusting the reviewer
script to match the engine without first understanding, and writing down, which
side is wrong and why.

## 4. Phase C — the engine on its own terms

- Full suites: `engine_v2/tests` (expected 116) and `audit/` (expected 29),
  green, with the counts confirmed rather than quoted.
- Determinism: build the payload in memory twice from the same CSV; identical
  bytes. (In memory, never via `regen.sh` — running that dirties both committed
  copies with a fresh `generated_at`.)
- All seven `*_ok` integrity keys true; `integrity.warnings` empty.
- The payments path in its current state: a header-only `payments.csv` yields
  paid 0, unpaid == above-contract, empty ledger, `paid_up_to` null.

## 5. Phase D — the pipeline joints

- Workbook → CSV: all 58 rows byte-compared (Phase 0 does this; recorded here
  as a criterion).
- CSV → JSON: in-memory rebuild equals the committed file, key for key,
  `generated_at` aside.
- Committed → live: byte comparison, done in Phase 0.
- The archive: newest hours export in `data/exports/` is byte-identical to the
  canonical CSV, so the audit trail actually contains what was adopted.

## 6. Phase E — the website

- `vue-tsc -b` and a production build, clean.
- The I9 grep audit: no arithmetic outside `format.ts`, and `format.ts`
  containing nothing beyond ÷60 and clock formatting.
- The 87-check rendered-DOM suite (`check-render.mjs`) against a local build —
  it must still pass now that the underlying real data has moved from the
  scenario files' 47-day snapshot: this specifically re-tests that the
  committed scenarios pin their *own* JSON, not today's.
- The live page read in a headless browser: headline owed, above-contract tile,
  days worked, monthly rows, weeks owing — each equal to the live JSON.

## 7. Phase F — the .tex document, claim by claim

The figure/rule/identity script from the document plan re-runs, but this phase
goes further: **every checkable sentence**, not just every number. In
particular:

- "145 automated checks run green" — counted, not believed;
- "the same spreadsheet always produces the same numbers" — phase C's
  determinism check is the evidence;
- "refuses to produce output at all if any fails" — verified by breaking one
  invariant's input in memory and confirming an exception, not a file;
- "each overnight shift under-counts by exactly one minute, never the reverse"
  — confirmed against the engine's error text and the audit report;
- the audit-history dates and finding counts against
  `docs/logic-audit_2026-07-06.md` as written;
- the derived hour figures (264.08, 138.50, 131.67, 470.87…) each recomputed
  from their minute values at two decimal places;
- the claim that 225 within-baseline minutes are "listed individually in the
  underlying data" — checked against `web_data.json`'s actual structure.

## 8. Phase G — the repo's own records

A sweep of `docs/TODO.md`, `docs/BUILD_NOTES.md`, `CLAUDE.md` and the two most
recent archived plans for factual claims now false — stale figure snapshots,
"six invariants" leftovers, schema-version references, counts. Cosmetic staleness
in *archived* plans is recorded but not edited; archives are photographs.

## 9. Phase H — the report

`notes/reviews/2026-08-18_full-review.md` (committed — it contains figures and
findings, nothing identifying):

- the commit hash and data state reviewed;
- a findings table, severity-ordered: anything that changes a published figure
  is CRITICAL; a wrong claim in a document is MAJOR; staleness is MINOR;
- every phase's PASS/FAIL with the actual evidence, including the hand-derived
  weekly tables;
- explicitly: what this review could *not* establish (the pay-week assumption,
  self-recorded hours, anything requiring a second person).

**Findings are reported, not fixed.** Fixes are proposed at the end and applied
only on approval — with one exception: if a CRITICAL finding means the live page
shows a wrong figure, I stop the review and say so immediately rather than
finishing the sweep first.

---

## Success criteria

1. Phase 0 pins the state: workbook↔CSV↔JSON↔live all in agreement (or the
   divergence named), commit hash recorded.
2. The independent reimplementation agrees with the engine on every figure
   listed in §3, including naming the source of the 225 within-baseline
   minutes — or each disagreement is written up as a finding.
3. All 12 weekly totals hand-summed and shown; two weeks worked in full.
4. Suites green with counts confirmed: 116 + 29; determinism shown; seven
   integrity keys true.
5. Website: type-check and build clean, I9 grep clean, 87 scenario checks pass,
   live DOM matches live JSON on the five headline figures.
6. Every number and every checkable prose claim in the .tex verified, each with
   its evidence line in the report.
7. Docs sweep done; stale claims listed.
8. The report exists, is committed, and ends with either "no finding changes
   any published figure" or the list of findings that do.

### Invariants during the review

- **Nothing in `engine_v2/` is written**, including by scripts (`regen.sh` is
  not run; payloads build in memory).
- **The working tree ends clean** and nothing is pushed except the final report
  commit.
- **The reviewer script stays independent**: no import from `afc_hours`, and no
  editing it into agreement after a mismatch without a written finding first.
- **`tmp/` stays uncommitted.**

## Explicitly out of scope

- Fixing anything found (proposed at the end, applied on approval — except the
  immediate stop on a CRITICAL live-figure finding).
- Re-auditing AfC itself: whether 06:00/20:00 and whole-day weekends are the
  *right reading* of the handbook was settled in July; this review checks the
  system against its stated rules.
- The pay-week confirmation — that is payroll's, and the .tex asks them.
- `money.py`, still non-existent.

## Order of work

1. [x] Phase 0 — pin the state.
2. [x] Phase A — spreadsheet internal consistency.
3. [x] Phase B — independent re-derivation, weekly tables.
4. [x] Phase C — engine suites, determinism, integrity.
5. [x] Phase D — pipeline joints.
6. [x] Phase E — website, scenarios, live DOM.
7. [x] Phase F — .tex claim-by-claim.
8. [x] Phase G — docs sweep.
9. [x] Phase H — write and commit the report; propose fixes if any.

### Worklog

All phases ran 2026-08-19; the evidence lives in the report rather than being
duplicated here. Phase counts: 0 — four byte-level agreements; A — 58 rows,
one finding (the Hours column rounds up, read by nothing); B — **92
independent comparisons, 0 disagreements**, the 225 within-baseline minutes
traced to Monday 20 July 20:00–23:45 and hand-verified; C — 145 tests green,
determinism shown, refusal-on-violation demonstrated via I6; D — in-memory
rebuild equals the committed JSON exactly; E — build clean, I9 audit clean
(only array indexing outside format.ts), 87 scenario checks pass, live DOM
matches live JSON; F — every checkable sentence in the .tex evidenced,
including the "listed individually" claim (weekly[W30].flagged_segments); G —
two stale-doc findings (project CLAUDE.md; audit/README run command). Nothing
critical, nothing major, no figure moved.
