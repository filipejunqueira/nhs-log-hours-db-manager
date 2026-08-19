# Full-system review — 2026-08-19

**Scope:** everything a reader can encounter — the spreadsheet, the engine, the
published JSON, the live page, the compiled audit document, and the repo's own
records — checked for mutual agreement, with the figures re-derived by an
independent implementation rather than re-asserted by the engine's own tests.

**Verdict: no finding changes any published figure.** Every number on the live
page, in `web_data.json` and in the audit document was reproduced independently
from the workbook, to the minute.

Five findings, all documentation-side, all now **applied** (2026-08-19). Two of
them — R4 and R5 — were uncovered while fixing the first three, and are the more
interesting ones: `audit/` described the wrong input file and inverted the
purpose of its own defect tests. Neither affects a figure, but both would have
misled anyone relying on that suite to know what is guarded.

**State reviewed:** commit `a833fc2`, working tree carrying only the review
plan; the workbook at `~/downloads/filipe_working_hours_log.xlsx` (mtime 18 Aug
19:29, the file ingested at 20:07); live page fetched 19 Aug.

---

## Method

The chain was checked at every joint, and the centrepiece is independence: a
scratch script (`rederive.py`, kept with the session scratchpad) that never
imports from `afc_hours`, reads the workbook directly, and classifies **every
worked minute individually** — a deliberately different algorithm from the
engine's segment-splitting. Two implementations agreeing on 58 days across
every category is evidence; one implementation agreeing with itself is none.

Honest limits: the same person wrote both sides; the bank-holiday table is
shared; and whether the rules are the right *reading of AfC* (in particular the
Monday pay-week) is outside what any internal check can establish — which is
why the audit document asks payroll to confirm the pay-week rather than
claiming it.

## Phase 0 — ground truth pinned

| check | result |
|---|---|
| workbook converts byte-identically to both canonical CSVs (58 rows + header-only payments) | PASS |
| two committed `web_data.json` copies byte-identical (sha `49aa01c0…`) | PASS |
| live page serves the committed bytes exactly | PASS |
| newest archived export byte-identical to the canonical CSV | PASS |

## Phase A — the spreadsheet against itself

58 rows. End after Start on every row; `Minutes` equals End − Start **exactly
on all 58** (so the engine's warning-tolerance is unused, matching its zero
warnings); one period per date; dates strictly increasing, all in 2026; no
Saturdays, five Sundays.

**Finding R1 (minor):** the `Hours` column rounds *up*, not to nearest — 22 of
58 rows are 0.01 h above `Minutes`/60 (e.g. 794 min = 13.233 h recorded as
13.24). Consequence today: none — the engine reads Date, Start, End and
Minutes only (`core.py:299-300`); `Hours` is carried verbatim and read by
nothing. Two forward-looking notes: (a) the parked TODO idea of cross-checking
the `Hours` column would flag 22 rows unless written round-up-aware; (b) if the
same spreadsheet habit ever computes `HoursPaid` on the payments tab, the
worst-case round-up error is 0.4 min against the engine's fatal 0.5-min
tolerance — it passes, but with a 0.1-min margin.

Plausibility, looked at rather than skipped: seven days over 12 h, including
four of 15.8–16.4 h on 20–23 July. Consistent with their notes. One observation
for the self-recorded-hours limitation: the 17 Aug row records 08:01 while its
own note says work started at 04:01 — the log under-records relative to its own
narrative, in the conservative direction, consistent with the audit document's
"never the reverse" stance.

## Phase B — independent re-derivation

**92 comparisons, 0 disagreements**: grand total (32 055), all three bands
(15 845 / 8 310 / 7 900), all five classes (28 312 / 1 044 / 0 / 2 699 / 0),
above-contract (16 210), within-baseline (225), all 12 weekly rows with their
per-week bands, all 3 monthly rows on every margin, day count, last cumulative
value.

Weekly totals, re-summed from the raw rows (contracted/additional/overtime):

| w/c | total | bands |
|---|---|---|
| 01 Jun | 3 407 | 1350 / 900 / 1157 |
| 08 Jun | 3 398 | 1350 / 900 / 1148 |
| 15 Jun | 2 555 | 1350 / 900 / 305 |
| 22 Jun | 3 259 | 1350 / 900 / 1009 |
| 29 Jun | 2 371 | 1350 / 900 / 121 |
| 06 Jul | 1 390 | 1350 / 40 / 0 |
| 13 Jul | 2 062 | 1350 / 712 / 0 |
| 20 Jul | 5 045 | 1350 / 900 / 2795 |
| 27 Jul | 2 856 | 1350 / 900 / 606 |
| 03 Aug | 1 708 | 1350 / 358 / 0 |
| 10 Aug | 3 009 | 1350 / 900 / 759 |
| 17 Aug | 995 | 995 / 0 / 0 |

The first four match the July audit's hand-derived table exactly.

**The 225 within-baseline minutes, traced to their origin:** Monday 20 July,
07:52–23:45 (953 min). As the first worked day of its week, all 953 minutes lie
inside the week's first 1 350, and the 225 of them after 20:00 are therefore
both contracted and unsocial. Hand-computed: end 23:45 = minute 1425;
1425 − 1200 = 225. The published JSON lists exactly this segment individually
(`weekly[W30].flagged_segments`: 2026-07-20, minutes 1200–1425,
weekday_night), confirming the audit document's "listed individually" claim.

## Phase C — the engine on its own terms

116 engine tests + 29 characterisation tests green (confirming the document's
"145" by count, not quotation). Two in-memory builds from the same CSV produce
identical bytes. All seven `*_ok` integrity keys true, `warnings` empty. The
header-only payments file yields paid 0, unpaid = above-contract, empty
ledger, `paid_up_to` null. Feeding `compute()` a duplicated day raises
`AssertionError: I6 per-day worked-minutes-exceed-span failed` and produces no
output — the "refuses rather than emits" claim, demonstrated.

## Phase D — pipeline joints

In-memory rebuild (same `generated_at`) equals the committed `web_data.json`
exactly, dict-for-dict. Together with Phase 0: workbook → CSV → JSON → live are
one unbroken chain of byte-level agreement.

## Phase E — the website

`vue-tsc -b` and the production build clean. The I9 audit, run over script code
only: the sole arithmetic outside `format.ts` is an array index
(`points.length - 1`); `format.ts` holds ÷60 and clock formatting and nothing
else. All 87 rendered-DOM scenario checks pass — notable because the scenario
files pin the 47-day snapshot, so this also re-confirms the check tests its own
JSON rather than today's. The live page, read in a headless browser, matches
the live JSON on owed headline (270.17 h), above-contract tile, days (58),
monthly rows (3) and weeks owing (11), with zero page errors.

## Phase F — the audit document, claim by claim

Every figure in the document was already script-matched against
`web_data.json` when it was written; Phase B independently re-derived those
same numbers from the workbook, closing the loop. Prose claims verified today:

- "145 automated checks run green" — counted: 116 + 29.
- "the same spreadsheet always produces the same numbers" — determinism shown.
- "refuses to produce output at all" — I6 violation raised, nothing emitted.
- overnight advice and the one-minute under-count — the engine's own error
  text instructs the 23:59/00:00 split; the un-recorded minute follows.
- audit history — six findings (F1–F6 counted in the report), the verdict
  sentence as quoted, all six addressed 2026-07-19 (TODO Done log, six
  commits), 29 pinning checks present and green.
- "listed individually in the underlying data" — confirmed, see Phase B.
- derived hour figures (264.08, 138.50, 131.67, 471.87, 17.40, 44.98, 3.75,
  534.25, 270.17) — each recomputed from its minute value.

## Phase G — the repo's records

**Finding R2 (minor):** the project `CLAUDE.md` is stale in two load-bearing
ways: it says the engine output is "schema 1.1.0" (it is 1.2.0) and that the
website is "not built yet" (live at 1.4.1 since 18 Aug). It is read at the
start of every session, so it actively misleads future work.

**Finding R3 (minor, already parked):** `audit/README.md:32` prints a run
command naming `test_characterisation.py`; the file is
`test_characterization.py`, so the command as printed fails. Already in TODO's
Later list; confirmed still present. *(Widened while fixing: the same wrong
filename appears twice more in the suite's own docstring, including a second
unrunnable run command.)*

**Finding R4 (moderate — found while applying the fixes):**
`audit/README.md` described the suite as pinning "the **current** real log
(`filipe_working_hours_log.csv`, 22 days)". It does not, and never has: it
reads the **frozen fixture** `engine_v2/tests/fixtures/hours_2026-07-14.csv`
(32 rows, 1 Jun – 14 Jul). That is the correct design — pinning the live log
would break these checks every time a day is added — and it is why all 29
stayed green when the log grew from 47 to 58 days. But a reader of the README
would have believed the suite guards today's published figures. It guards the
engine's behaviour against a fixed input, which is a different and more useful
thing. The same paragraph also carried finding F1 as still open; F1 was fixed
2026-07-19.

**Finding R5 (moderate — found while applying the fixes):** the README, and
the suite's own docstring, both said the `test_defect_*` checks pin **current
defective** behaviour and would "fail once a fix lands". The reverse is true:
all four defects (D1, D2, D2b, D3) were fixed on 2026-07-19 and the tests were
rewritten then to pin the *corrected* behaviour — their names end `_after_f2`,
`_after_f4`, `_after_f3`, and no test is named `test_defect_*` at all any more.
As written, the documentation inverted the direction of the safety net.

`docs/BUILD_NOTES.md` claims all still hold (the ≥ 1.1.0 schema gate correctly
admits 1.2.0). Archived plans were left as photographs.

## What this review could not establish

- **That Monday is the Trust's pay-week boundary.** Assumed in `rules.py`,
  flagged there and in the audit document; decides the additional/overtime
  split (never the total). Payroll's to confirm.
- **That the recorded hours were worked.** Self-recorded; the drift gate stops
  retroactive edits, but nothing here witnesses a day. (The 17 Aug observation
  above cuts in the conservative direction.)
- **Independence from a shared misreading.** Both implementations were written
  by the same reviewer against the same prose rules.

## Findings and proposed fixes (none applied)

| # | severity | finding | proposed fix |
|---|---|---|---|
| R1 | minor | spreadsheet `Hours` column rounds up; 22/58 rows +0.01 h; read by nothing | none needed in code; note kept here. If the payments tab ever computes `HoursPaid`, prefer `=ROUND(minutes/60,2)` |
| R2 | minor | project `CLAUDE.md` stale: "schema 1.1.0", website "not built yet" | three-line edit bringing it to 1.2.0 / built-and-live |
| R3 | minor | run command names a file that does not exist — in `audit/README.md` **and twice in the suite docstring** | spelling fixed in all three places; the English word "characterisation" left British |
| R4 | moderate | `audit/README.md` said the suite pins the current 22-day real log; it reads the frozen 32-day fixture, and carried the fixed F1 as open | rewritten to state the fixture, why frozen is deliberate, and that F1 is closed |
| R5 | moderate | README and suite docstring both inverted what the defect tests do — they pin the *fixed* behaviour, not the defects | both corrected |

**All five applied 2026-08-19** on the user's instruction. R1 needed no code
change (a note for the spreadsheet, kept above). R2–R5 were documentation
edits; both suites re-run after each (116 + 29 green), and the corrected run
command was executed to prove it works.
