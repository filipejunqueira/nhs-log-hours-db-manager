# NHS-hours — Fable LOGIC AUDIT pass (paste into a fresh Claude Code / Fable session)

**Today's job = audit the correctness of the working-hours ENGINE logic. NOT the website.**
The Vue site is trivial and will be built later on Opus/CC. This pass exists because the engine
computes real working hours (records/pay implications) — a subtle bug is costly, so it's worth
Fable's careful reasoning.

## Start here
`cd ~/code/nhs-hour-log` — repo-only project; the engine is on this container's disk, read it
directly. Read the code AND `plan.md` (the website-scaffold plan) to recover intended behaviour.

## What to audit (the working-hours engine)
Reconstruct the intended rules from the code, then systematically check the logic for
correctness. Pay specific attention to the usual failure modes for hour-tracking engines:
- **Rounding** — where/when hours are rounded, and whether rounding compounds across entries.
- **Boundaries** — day/week/month boundaries; entries that span midnight; partial days.
- **Time arithmetic** — timezone/DST transitions (a shift across a clock change), off-by-one on
  inclusive/exclusive end times, minutes-vs-decimal-hours conversions.
- **Breaks / unpaid time** — subtraction logic, negative or zero-length segments.
- **Overtime / special rates** — thresholds, and whether they double-count at boundaries.
- **Bank holidays / weekends / night shifts** — classification edges.
- **Aggregation** — summing across a week/period; whether a missing or malformed entry silently
  drops or corrupts a total.
- **Input validation** — overlapping shifts, end-before-start, duplicate entries.

## Method
1. Read the engine + plan.md; write down the intended rules in your own words FIRST.
2. Go rule-by-rule and adversarially look for where the implementation diverges from intent.
3. For each finding: state the input that triggers it, the wrong output, and the correct output.
4. Produce a **characterisation test suite** that pins the CORRECT behaviour (these tests are the
   durable value — they protect the engine when the site is built later).
   The `claim-verify` and `systematic-diagnostic-reasoning` skills are available if useful.

## Deliverable
An audit report (`nhs-hour-log/logic-audit_2026-07-06.md`) with findings ranked by severity +
recommended fixes, and the test suite. Apply low-risk fixes if confident; flag anything
ambiguous for Filipe rather than guessing at intended policy.

## Boundaries
- Do NOT build or scaffold the Vue website (deferred to Opus).
- Repo-only by project rule — keep everything inside `~/code/nhs-hour-log`.
- Do NOT touch the desktop / wakectl (tonight's separate session).
