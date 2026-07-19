# AfC Hours Engine — Audit Brief

This document describes a Python program for an independent reviewer. Its purpose
is to let the reviewer cross-check the program's logic. It states what the program
is intended to do and what it is built from. It lists input scenarios to consider,
but deliberately does **not** state the expected output for any scenario, so that
the reviewer derives expected results independently and compares them against the
code's behaviour.

The program is Part (i) of a larger system. A separate financial layer (Part ii)
is **not yet written** and is out of scope for this audit.

**Revision note (output schema 1.1.0).** Since the first audit, the following were
added in response to its findings: same-date overlapping/duplicate periods are now
rejected (previously summed); a per-day "worked minutes ≤ clock span" runtime
invariant was added and is reported in the integrity block as `span_ok`; the
`End ≤ Start` rejection now distinguishes zero-length from End-before-Start; a
non-ISO dotted date is reported as an unrecognised format rather than ambiguous;
non-zero seconds are rejected rather than truncated; and the statistics
denominator is documented. None of these change any figure emitted for
well-formed input.

---

## 1. What the program is, and what it computes

### 1.1 Purpose and context
The program takes a log of working start/end times for one part-time worker and
computes how those working minutes distribute across (a) contractual thresholds
and (b) unsocial-time categories, within a defined pay-week. It writes the result
as a single JSON file intended to drive a public dashboard.

The post is part-time: a contracted **22.5 hours per week**, against a full-time
equivalent of **37.5 hours per week**. The worker has been working above contracted
hours during a handover period and wants the extra hours represented transparently.

The program computes **hours only**. It does not compute pay, rates, or money of
any kind. Pay rates are intended to be applied separately, by a reader of the
output (e.g. payroll), and by the not-yet-built Part (ii).

### 1.2 Input specification
- A CSV file with columns `Date`, `Start`, `End`, and an optional `Minutes` column.
  Column matching is case-insensitive. Additional columns are ignored.
- One row represents one continuous worked period.
- **Date** is accepted as ISO `YYYY-MM-DD` or as an explicit month-name form
  (e.g. `1-Jun-2026`, `1 June 2026`); month-name forms also accept a two-digit
  year (e.g. `1-Jun-26`, read as 2026 -- an out-of-window year still dies at
  the bank-holiday year guard). A purely numeric non-ISO date
  (e.g. `01/06/2026`) is treated as ambiguous and rejected.
- **Start** and **End** are 24-hour `HH:MM` (seconds `HH:MM:SS` also accepted).
- The worker's measured unit is **minutes**; clock times are recorded to the minute.

### 1.3 Output specification
- A single JSON file. All durations in it are **integer minutes**; the file
  contains no hours and no monetary values.
- The file has two top-level blocks:
  - `meta`: a schema version, a generation timestamp, the unit declaration, the
    fixed rule constants (thresholds, clock boundaries, pay-week start, the
    bank-holiday dates used and the years they cover), and a plain-language
    methodology description.
  - `content`: the period covered; grand totals; per-week summaries; a per-day
    log; a band×class cross-tabulation; a cumulative running-total series; a set
    of derived statistics; and an integrity block reporting the runtime checks.

### 1.4 Internal computation (stated behaviour)
- **Unit.** All computation is in integer minutes. There is no floating-point
  arithmetic in the hours path and no rounding. (Derived statistics such as
  percentages and means are the only floating-point values, and are presentational.)
- **Pay-week.** A pay-week runs Monday to Sunday. Worked minutes are grouped by
  the Monday that begins their week.
- **Threshold banding.** Within each pay-week, worked minutes are attributed in
  chronological order of when they were worked. The first **1350** minutes
  (22.5h) are classified `contracted`; minutes from 1350 up to **2250** (37.5h)
  are `additional`; minutes beyond 2250 are `overtime`.
- **Unsocial classification by clock time.** On a weekday, minutes worked between
  06:00 and 20:00 are `daytime`; minutes worked between 20:00 and 06:00 are
  `weekday_night`. A Saturday, a Sunday, and a bank holiday are each treated as a
  single whole-day class (`saturday`, `sunday`, `bank_holiday`) with no intra-day
  06:00/20:00 split.
- **Bank holidays.** A fixed table of England & Wales bank-holiday dates is used,
  covering specific years. Bank-holiday classification takes precedence over the
  weekday/weekend determination for that date.
- **Segmentation.** A worked period that crosses a clock boundary (06:00 or 20:00)
  or a threshold boundary (1350 or 2250 cumulative minutes) is split at the exact
  minute, so that every resulting atomic piece carries exactly one threshold band
  and exactly one unsocial class.
- **Within-baseline flag.** Any minute that is classified as both `contracted`
  (within the first 22.5h of its week) and as some unsocial class (not `daytime`)
  is counted into `unsocial_within_baseline` and listed individually.
- **Statistics.** Percentages of time per band and per class, mean minutes per day
  and per week, mean start and end clock-minute, longest and shortest day, days
  worked, days touching each class, and a cumulative running total by date. Means
  are taken over the days and weeks in which work was recorded, not over every
  calendar day or week in the period.
- **Determinism and guarantees the program is intended to hold.** The hours
  computation is intended to be a pure function of the input CSV: it takes no
  options or flags, reads no wall-clock, and uses no randomness, so the same CSV
  is intended to yield identical numbers every time. The JSON `content` is
  intended to be byte-identical across runs for a given input; only the `meta`
  timestamp varies. The hours path is intended not to import any money/rate logic.
- **Runtime invariants.** On every run the program asserts a set of internal
  consistency checks and aborts (raises) rather than emit output if any fails.
  The checks concern conservation of minutes, exhaustion of the total by each of
  the two partitions (band and class), the threshold-banding formula, cross-tab
  reconciliation, and a per-day check that worked minutes do not exceed the day's
  clock span (latest end minus earliest start).

### 1.5 Input handling that ends in a hard error (stated behaviour)
The program is intended to refuse to run, with an error naming the offending
row(s), in these situations: a period whose End equals its Start (zero length); a
period whose End precedes its Start on the same day (including a single-row
overnight shift, which is not supported -- the error advises splitting into a
row ending 23:59 and a row starting 00:00, which deliberately un-records the
23:59-00:00 minute: each overnight shift under-counts by exactly one minute,
never the reverse); two periods on the same date that
overlap or duplicate (touching endpoints are allowed, so split and contiguous
shifts are fine); a date in a year the bank-holiday table does not cover; a
slash- or dash-separated numeric date (ambiguous day/month order); a date in any
other unrecognised format; a time with non-zero seconds; a time not in HH:MM(:SS)
form; a row missing Date, Start, or End; a missing required column; and empty
input (no usable rows). A row that disagrees between its `Minutes` column and the
recomputed duration is intended to be recorded as a non-fatal warning, with the
recomputed value used.

---

## 2. Files and structure

```
engine_v2/
  afc_hours/            the Python package
    __init__.py         package marker; describes the module dependency graph
    rules.py            constants only ("the law"): thresholds, pay-week start,
                        clock boundaries, bank-holiday dates and years covered.
                        No logic, no functions, no money.
    core.py             Part (i): CSV ingest + validation, day/clock
                        classification, threshold banding, statistics, and the
                        runtime invariants. The deterministic hours computation.
                        Imports rules.
    emit.py             serialises the computed result to the JSON file
                        (minutes only). Imports core and rules.
    (money.py)          Part (ii), NOT PRESENT. Will hold rates/variants later.
  tests/
    test_rules.py       checks the constants (values, bank-holiday weekdays,
                        internal consistency, constants-only/no-money guards).
    test_core.py        checks ingest guards, classification, banding, the
                        within-baseline flag, the invariants, and re-derives
                        weeks of the real log by hand.
    test_emit.py        checks JSON shape, determinism, minutes-only, and that
                        the output and module carry no money.
  data/
    filipe_working_hours_log_25-06-2026.csv   the real sample input
  web_data.json         a sample emitted output (from the sample input)
```

Intended dependency direction is one-way: `rules` is imported by `core`, and
`core`/`rules` are imported by `emit`. The future `money` module is intended to
read the result object that `core` produces, and never to be imported by `emit`.

The package targets **Python 3.10+** (it uses `X | None` type unions and built-in
generic types). It has **no third-party dependencies**; the standard library only.

Tests are runnable standalone, e.g. `python3 tests/test_core.py`, or under
`pytest`. They locate the sample CSV relative to the package (overridable via the
`AFC_REAL_LOG` environment variable).

---

## 3. Input scenarios to consider (inputs only; no expected outputs given)

These are inputs a reviewer may wish to reason through or construct. Expected
results are intentionally omitted.

### 3.1 Weekly totals and threshold boundaries
- A pay-week whose total is below 1350 minutes (e.g. two weekday periods of 600).
- A pay-week whose total is exactly 1350 minutes (e.g. three periods of 450).
- A pay-week whose total is strictly between 1350 and 2250 (e.g. 1800).
- A pay-week whose total is exactly 2250 minutes.
- A pay-week whose total exceeds 2250 minutes (e.g. 2400).
- A pay-week in which a single worked period straddles the 1350 boundary
  (cumulative reaches 1350 partway through one period).
- A pay-week in which a single worked period straddles the 2250 boundary.
- The same set of rows presented in different orders within the file (shuffled,
  reversed).

### 3.2 Clock boundaries (weekday)
- A weekday period entirely within 06:00–20:00 (e.g. 08:00–18:00).
- A weekday period beginning before 06:00 (e.g. 05:00–09:00).
- A weekday period ending after 20:00 (e.g. 17:00–22:00).
- A weekday period ending exactly at 20:00; beginning exactly at 06:00; ending at
  19:59; beginning at 20:00.
- A weekday period spanning the whole working day and beyond (e.g. 05:00–22:00).
- A weekday period of one minute at a boundary (e.g. 19:59–20:00, 20:00–20:01).

### 3.3 Day type
- A Saturday period, including one spanning 20:00 (e.g. 10:00–22:00).
- A Sunday period.
- A bank holiday that falls on a weekday (e.g. 2026-08-31).
- A bank holiday that is itself a substitute day (e.g. 2026-12-28; 2027-12-28).
- A Saturday or Sunday immediately adjacent to a bank holiday.
- 25 December on a year where it is a weekend and the holiday is observed on a
  later weekday (e.g. 2027-12-25).

### 3.4 Pay-week grouping
- Work spanning a Sunday into the following Monday (crossing the pay-week edge).
- A Sunday worked early in its week versus the same Sunday worked after a full set
  of weekday hours.
- A pay-week containing a single worked day.
- A run of weeks with a gap week (no work) in the middle.
- Work that begins on the worker's first day mid-pattern (a partial first week).

### 3.5 The within-baseline flag
- A week whose only (or first) worked period is unsocial (e.g. a lone Sunday).
- A week in which unsocial work occurs only after 1350 minutes are reached.
- A week mixing a pre-1350 weekday-evening period and a post-1350 Sunday period.

### 3.6 Multiple periods and overlaps
- Two separate periods on the same date with a gap between them (split shift).
- Two contiguous periods on the same date (one ends, the next begins).
- Two periods on the same date that overlap in time (e.g. 09:00–12:00 and
  11:00–14:00).
- Many short periods on one date.

### 3.7 Malformed, edge, and guard inputs
- A period whose End is not after its Start (e.g. 22:00–02:00; 17:00–09:00).
- A period whose End equals its Start (zero duration).
- A date in a year outside the bank-holiday table (e.g. 2025; 2028).
- An ambiguous numeric date (e.g. 01/06/2026; 6/1/26).
- A date in an unrecognised format (e.g. `June 1st`; `2026.06.01`).
- A time not in HH:MM (e.g. `9am`; `0900`; `25:00`; `08:60`).
- A row missing Start, or End, or Date.
- A fully blank line within the file.
- A CSV lacking one of the required columns.
- A CSV with only a header row (no data).
- A `Minutes` column value that disagrees with End−Start.
- A `Minutes` column value that is non-numeric or blank.
- Extra/unknown columns present.
- Times given with seconds (HH:MM:SS).
- A file beginning with a byte-order mark (BOM) or using `utf-8-sig`.
- A maximal single day (e.g. 00:00–23:59).
- Midnight values (00:00 as a start; 23:59 as an end).
- Duplicate rows (identical date/start/end appearing twice).

### 3.8 Statistics-sensitive inputs
- A dataset with exactly one working day.
- A dataset in which some unsocial class never occurs (e.g. no Saturdays).
- A dataset in which every day is identical.

### 3.9 Real data
- The supplied `filipe_working_hours_log_25-06-2026.csv` (21 working days across
  four ISO weeks, including two Sundays and three weekday periods extending past
  20:00).

---

## 4. What to provide to the reviewing tool, and how to run it

Provide the entire `engine_v2/` folder. The relevant files are:

- `afc_hours/__init__.py`
- `afc_hours/rules.py`
- `afc_hours/core.py`
- `afc_hours/emit.py`
- `tests/test_rules.py`
- `tests/test_core.py`
- `tests/test_emit.py`
- `data/filipe_working_hours_log_25-06-2026.csv`
- `web_data.json` (sample output)
- this `AUDIT_BRIEF.md`

Scope notes for the reviewer:

- Only the `engine_v2/` package is in scope. The financial layer (`money.py`) and
  any command-line wrapper are not yet written and are not part of this audit.
- Any older files outside `engine_v2/` are unrelated to this version and should be
  ignored.

Running the checks (no third-party packages required; Python 3.10+):

```
python3 tests/test_rules.py
python3 tests/test_core.py
python3 tests/test_emit.py
```

or, if available:

```
pytest tests/
```

To regenerate the sample output from the sample input:

```
python3 -c "from afc_hours import core, emit; emit.write_json(core.compute_from_csv('data/filipe_working_hours_log_25-06-2026.csv'), 'web_data.json')"
```
