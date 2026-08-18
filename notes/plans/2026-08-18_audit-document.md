# Plan: the audit document (`tmp/afc_hours_record_2026-08-18.tex`)

**Goal:** one document that answers, for whoever asks, *"where does the number on
that page come from, and why should I believe it?"* — readable by payroll or
Vince in its first page, and sufficient for an independent reviewer in the rest.

STATUS: **CLOSED 2026-08-18.** All seven criteria evidenced — the user ran
`awesome-latex` and confirmed the PDF compiled.

Closes the `.tex` audit document item in `docs/TODO.md`'s Later list.

Decided with the user 2026-08-18, **revised the same day**:
- **NOT committed — neither the `.tex` nor the `.pdf`.** It lives in `tmp/`,
  which is gitignored, beside the two reference documents. This replaces the
  earlier "in the repo, identity-light" choice and resolves the tension behind
  it: the repo is public, so the way to have a fully identified document is to
  keep it out of the repo, not to strip the identity out of the document;
- **it identifies the author fully** — `\name`, `\position`, `\address`,
  `\email`, exactly as `bhly_database_2026-07-23.tex` does. It is an internal
  NHS document, not a repository artefact;
- **the readers are Vince and payroll**, and it will be forwarded internally by
  email. Interpretation, stated rather than assumed: the "summary first, then the
  technical body" shape stands, but the writing is aimed at those two readers.
  The technical sections are supporting evidence a reader may skip, not a
  reviewer's manual, and the reproduction commands shrink to a short appendix;
- **the whole system**, not the engine alone: the figure is produced by the
  workbook conversion, the engine, the reconciliation and the publish step
  together.

---

## 0. The constraint that shapes the work

**It cannot be compiled here.** There is no TeX in this container, and
`super-awesome.cls` only builds inside `texlive/texlive:TL2023-historic` (its own
header says a host TeX Live install is a dead end). The Docker socket is mounted
but the CLI is absent and the API does not answer.

So the LaTeX must be written conservatively and stay close to what is already
known to compile. Every construct used is one the two documents in `tmp/` already
use: `\cvsection`, `\cvsubsection`, `cvparagraph`, `itemize`, `tabularx` with the
`L`/`C` column types they define, `booktabs` rules, and a local `\code{}` macro.
**Nothing else.** No new packages, no `lstlisting` beyond the single use the
reference documents already make of it, no TikZ, no custom environments.

The last success criterion is therefore the user's to run, and until they do the
document is *unverified*, not *done*.

## 1. Sources, and how current each one is

| source | lines | what it gives | currency |
|---|---|---|---|
| `engine_v2/AUDIT_BRIEF.md` | 296 | purpose, input/output spec, stated behaviour, refusal list, scenario families | **schema 1.1.0** — predates payments, the monthly block and the workbook |
| `docs/logic-audit_2026-07-06.md` | 238 | the independent audit: verdict, F1–F6, the two non-obvious proofs, hand re-derivation | historical, and the findings are now fixed |
| `audit/README.md` + `test_characterization.py` | 36 + 16 KB | what is pinned, and the defects D1–D3 | current; D1/D2/D2b/D3 all marked FIXED 2026-07-19 |
| `engine_v2/afc_hours/rules.py` | 106 | the law itself: thresholds, pay-week, clock boundaries, bank holidays | **current, and quotable** |
| `engine_v2/afc_hours/core.py` | — | I1–I7 as coded, with the assertion messages | current |
| `engine_v2/afc_hours/payments.py` | — | I8, the note guard, the money-token list | current |
| `scripts/*.sh`, `scripts/xlsx_to_csv.py` | — | the pipeline as it now stands | current, as of today |

**Two things in the TODO line are stale and the document must not inherit them.**
It says "six invariants"; there are **nine** — I7 monthly conservation and I8
reconciliation landed with schema 1.2.0, and I9 (no arithmetic in the browser)
was discharged when `sumMinutes` was deleted. And `AUDIT_BRIEF.md` describes a
21-day sample at schema 1.1.0; the live system is 1.2.0 over 58 days with a
payments layer.

## 2. Structure

Ten sections. Sections 1–2 are the part a non-technical reader needs; 3 onwards
is the record.

1. **Summary.** What the system does, what it refuses to do, and the one-line
   assurance: the hours computation is a pure function of the log, it asserts
   nine invariants on every run and *aborts rather than publish* if any fails,
   it has been independently audited, and 145 automated checks run green.
2. **What is counted, and what is not.** Contracted 22.5 h against a 37.5 h
   full-time week; the three bands; the four unsocial classes; what "owed"
   means and how it is settled. Plainly stated: **no monetary value is computed
   or displayed anywhere in this system**, by construction, not by policy.
3. **The rules as law.** From `rules.py`, which exists precisely so the rules
   have one home: thresholds, the Monday pay-week, the 06:00/20:00 boundaries,
   the whole-day weekend and bank-holiday rule, the bank-holiday table and the
   year guard that refuses to classify a date outside it. Each with its AfC
   citation as the file gives it.
4. **The pipeline.** Workbook → two CSVs → engine → reconciliation → published
   JSON → page, with the gate at each step: validate before copying, drift gate,
   collision-proof archive, integrity checks before the file is replaced, and a
   publish that is a deliberate human act. One `tabularx`, no diagram — a TikZ
   figure would be the most likely thing to fail a first compile.
5. **The nine invariants, with proofs.** Each: what it asserts, where it is
   asserted, and what a violation would mean. The two non-obvious ones carry the
   arguments the audit set out — that classifying each clock segment by its start
   is sound because no segment contains a boundary in its interior, and that
   comparing only adjacent sorted periods is sufficient to reject all overlaps.
6. **What the system refuses.** The hard-error list, including the payments ones:
   an `HoursPaid` that contradicts `MinutesPaid`, a note containing a money word,
   duplicate payments. With the reason refusal is preferred to a guess.
7. **Audit history.** 2026-07-06 independent audit and its verdict; F1–F6; the
   fixes applied 2026-07-19 and the characterisation suite adopted as the suite
   of record; schema 1.1.0; schema 1.2.0 on 2026-08-17; the rendered-page check
   and the workbook pipeline on 2026-08-18.
8. **Known limitations.** Stated plainly, because an audit document that only
   lists strengths is not one — see §3 below for the list.
9. **Reproducing every figure.** Exact commands, from a clone to the published
   JSON.
10. **The figures as they stand**, dated 18 August 2026, marked as a snapshot so
    the document does not read as though it were describing today forever.

## 3. The limitations section, in full

These go in, not because they are required, but because the document is worthless
if a reader finds one of them itself and wonders what else was left out.

- **The Monday pay-week boundary is assumed, and unconfirmed against LTHT's ESR
  definition.** `rules.py` says so itself. It matters, because the boundary
  decides which minutes cross 37.5 h and therefore which are overtime.
- **A single overnight shift is not supported and must be split**, which
  deliberately un-records the 23:59–00:00 minute. Each overnight shift
  under-counts by exactly one minute — never the reverse.
- **The `Minutes` column is a cross-check, not a source.** Where it disagrees
  with End − Start the recomputed value wins and a warning is raised.
- **Bank holidays cover 2026 and 2027 only.** A date outside those years is
  refused rather than silently mis-classified.
- **`money.py` does not exist.** Nothing here converts hours to money, so no
  figure in this document or on the page is a monetary claim.
- **The hours log is committed to a public repository and its notes name
  colleagues.** Pre-existing, flagged, and outside this document's scope — but a
  reader of the repo will see it, so the document says so first.
- **Not every figure has been checked by a second person.** The engine's
  arithmetic was independently audited; the pipeline and website changes since
  are covered by automated checks and by the evidence in `notes/plans/`.

## 4. What the document must not do

- Carry a name, a position, an email, or anything else identifying. The reference
  documents in `tmp/` all do; this one must not, and that difference is
  deliberate.
- Quote a colleague's name from the log's notes.
- State or imply a monetary amount, a rate or a multiplier.
- Restate `AUDIT_BRIEF.md`'s 1.1.0-era figures as though current.
- Introduce a LaTeX construct not already used by the two reference documents.

---

## Success criteria

1. **It compiles.** `awesome-latex docs/audit-record.tex` produces a PDF with no
   errors. **This one is the user's to run** — see §0. Until then the document is
   unverified, and the plan says so rather than implying otherwise.
2. **Every figure in it matches the engine.** A script re-reads
   `engine_v2/web_data.json` and confirms each number quoted in §10 — total
   minutes, days, weeks, the three bands, the four classes, above-contract, owed,
   the month list — against the document source. No hand-copied figure.
3. **The rules quoted match `rules.py` exactly**: 1350, 2250, Monday, 06:00,
   20:00, the whole-day flag, 16 bank-holiday dates, years {2026, 2027}. Checked
   by script against the module, not by eye.
4. **Nine invariants, each with what it asserts and where.** `grep` finds I1–I9
   in the source, and the seven `*_ok` keys named in the document are exactly the
   seven the engine emits.
5. **Nothing monetary, and no colleague named.** No `£`, `$`, `€` and no money
   word from the engine's own token list, because the system computes no money
   and the document must not imply one; and no colleague's name lifted from the
   log's notes, even though the recipients are colleagues. The author's own
   details are present by design. Checked by script over the `.tex`.
   **Neither file is committed** — `git check-ignore` confirms `tmp/` covers
   both, and `git status` stays clean after they are written.
6. **Every command in §9 runs.** Each is executed in a clean clone and its output
   matches what the document says it produces.
7. **Only known-good LaTeX.** The set of `\begin{...}` environments and
   `\cv*`/`\make*` macros used is a subset of those in the two `tmp/` documents.
   Checked by script.

### Invariants

- **The document never becomes a source of figures.** Every number in it is
  reproducible from the engine by a command printed in the document itself. If
  the two disagree, the engine is right.
- **Nothing identifying is committed.** This is the project's standing rule and
  the document is the most likely thing to break it.
- **No claim without a source.** Every assertion traces to `rules.py`, the audit
  report, a test, or a script in this repo — and where something is assumed
  rather than verified (the pay-week boundary), the document says so.

## Explicitly out of scope

- **Changing anything in `engine_v2/`.** The document describes; it does not fix.
  The lock stays on and no lift is needed.
- **`money.py` and Part (ii).** Does not exist; the document says so and stops.
- **Re-running the 2026-07-06 audit.** Its findings are recorded as history, not
  re-litigated.
- **The colleague-names exposure.** Named as a limitation, not solved here.
- **Publishing the PDF anywhere.** The `.tex` is committed; whether a built PDF
  is committed or shared is a separate decision (see the open question below).

## Settled: nothing is committed

The open question about the PDF is closed by the same decision — neither file
goes into git. What the repo keeps is this plan and a Done-log entry recording
that the document exists, where it lives and what it says, so a future session
knows it is there without the document itself being public.

## Order of work

1. [ ] Write `docs/audit-record.tex`, sections 1–10.
2. [ ] Criteria 2–5 and 7 by script, against the `.tex` source.
3. [ ] Criterion 6: run every reproduction command in a clean clone.
4. [ ] Hand to the user for criterion 1, the compile. Fix whatever it reports.
5. [ ] Settle the PDF question; commit.
6. [ ] `docs/TODO.md`: move the item out of Later into the Done log.

### Worklog

**Written 2026-08-18 as `tmp/afc_hours_record_2026-08-18.tex`**, nine sections,
following the naming convention of the two reference documents beside it.

**Criteria 2 to 5 and 7 — PASS**, all by script against the `.tex` source rather
than by eye:

- **Every figure traces to the engine.** All nine minute figures and their hour
  equivalents, the day count (58), the pay-week count (12), the weeks still owing
  (11) and the period end were each read out of `engine_v2/web_data.json` and
  found in the document. Nothing was hand-copied. The thousands separator meant
  the check had to look for `32\,055` as well as `32055`.
- **Every rule matches `rules.py`**, read from the module rather than transcribed:
  22.5 and 37.5 hours, 1350 and 2250 minutes, Monday, 06:00, 20:00, the whole-day
  weekend rule, 16 bank-holiday dates, years {2026, 2027}.
- **All nine invariants named**, and the seven `*_ok` keys the engine emits are
  the seven described — I8 and I9 are asserted elsewhere and the document says so.
- **Nothing monetary, nobody named.** No currency symbol anywhere and no
  amount-shaped figure. Checked against the log's *actual* colleague names ---
  Vince, Mark, John, Lizzi, Lizzie, Dani, Andrea, Raj --- none of which appears.
- **No LaTeX the reference documents lack.** The set of environments and
  `\cv*`/`\make*`/`\set*` macros used is a strict subset of theirs, which is the
  only defence available against a first compile that cannot be run here.
- **Not committed.** `git check-ignore` confirms `tmp/` covers it and
  `git status` stays clean.

**Criterion 5 was revised, and the reason matters.** As written it said "no money
word from the engine's own token list". That is the right rule for a CSV note
destined for a public data file and the wrong one for prose whose entire point is
that no money is computed: the document necessarily contains "rate", "rates",
"multiplier" and "salary", every one of them inside a sentence denying that such
a thing is applied. The criterion is now **no currency symbol, no amount-shaped
figure, and every money word appearing only in a denial** — each of the five
occurrences was read back and confirmed to be exactly that.

Two apparent failures on the first run were faults in the checking script, not
the document, and were proved so before being changed: the only `$` in the file
is `$\times$` in `I5`'s description, and the crude name-extraction had flagged
"Monday" and "That" as colleagues.

**Criterion 1 — the compile — is outstanding and is the user's to run.** No TeX
here, and the Docker route is unavailable. Until `awesome-latex` has run, the
document is *unverified*, not *done*.

**Criterion 6 was dropped**, deliberately. The plan called for a section of
reproduction commands, run in a clean clone. Once the audience narrowed to Vince
and payroll, a page of shell commands stopped serving the reader: section 8 now
says the figures are reproducible, that the published page carries the same
numbers, and that the file wins over the document if they ever disagree — which
is the part a reader of this document actually needs. The commands themselves
remain in `engine_v2/AUDIT_BRIEF.md` §4 for anyone who wants them.

### Closed 2026-08-18

Criterion 1 evidenced: the user compiled the document with `awesome-latex` and
confirmed the PDF built. That was the one check that could not run in this
environment. The document and its PDF stay in `tmp/`, uncommitted, per the
decision at the top of this plan.
