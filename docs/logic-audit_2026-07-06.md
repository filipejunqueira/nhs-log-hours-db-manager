# Logic audit of the AfC hours engine (engine_v2) — 2026-07-06

**Verdict: the engine's hours arithmetic is correct.** Every rule in
`AUDIT_BRIEF.md` §1.4–1.5 was re-derived independently and probed empirically
(§3 scenario families); banding, clock classification, bank holidays, pay-week
grouping, the within-baseline flag, statistics denominators, determinism and
the emitted JSON all behave as specified. The committed `web_data.json` content
block byte-matches a fresh recomputation from the current CSV. **No finding
overstates worked hours**; nothing here changes any figure payroll would see.

What the audit did find: the engine's **own regression suite is broken against
the current repository state** (F1, the only high-severity item), two small
robustness defects in the optional `Minutes` cross-check path (F2, F4), one
defence-in-depth gap in the invariant net (F3), and two documentation
divergences (F5, F6). Fixes are **recommended but not applied**: `engine_v2/**`
is locked (deny rule in `.claude/settings.json` + CLAUDE.md), so each finding
carries a patch for Filipe to apply deliberately.

A companion characterisation suite pinning correct behaviour — and pinning the
defects so any fix is a visible change — lives in
[`audit/test_characterization.py`](audit/test_characterization.py)
(29 checks, all passing; stdlib-only, same conventions as the engine's tests).

---

## 1. Baseline: the engine's own tests cannot run green

Run on this snapshot (`python3 tests/test_*.py` from `engine_v2/`):

| Suite           | As committed                        | With `AFC_REAL_LOG` → current CSV |
| --------------- | ----------------------------------- | --------------------------------- |
| `test_rules.py` | **11/11 pass**                      | 11/11 pass (no CSV dependency)    |
| `test_core.py`  | 32/39 — 7 ERROR `FileNotFoundError` | 37/39 — 2 FAIL (stale figures)    |
| `test_emit.py`  | 1/17 — 16 ERROR `FileNotFoundError` | 14/17 — 3 FAIL (stale figures)    |

Cause, in two parts:

1. `test_core.py:20-22` and `test_emit.py:16-18` default to
   `data/filipe_working_hours_log_25-06-2026.csv`. Commit `954f4c5` renamed the
   data file to `filipe_working_hours_log.csv` (and extended it to 26 Jun)
   without touching the tests, so every real-log test errors out.
2. Even pointed at the current CSV, five tests pin the superseded 21-day
   snapshot: total 11 919, overtime 2 919, 21 daily/cumulative entries
   (`test_core.py:230,253`; `test_emit.py:60-61,77,93-95`). Current truth is
   12 619 / 3 619 / 22 (verified by hand, §3).

### F1 — HIGH (process): stale regression suite on a locked engine

The engine is "locked" partly on the strength of "67 checks, all passing"; that
guarantee is currently unverifiable, and will silently rot further with each
data update. Recommended patch (in `engine_v2/tests/`, currently denied):

```diff
--- a/engine_v2/tests/test_core.py        (same one-line change in test_emit.py)
-    "data", "filipe_working_hours_log_25-06-2026.csv")
+    "data", "filipe_working_hours_log.csv")
```

plus refreshed pins: total `11919 → 12619`, overtime `2919 → 3619`, day count
`21 → 22`, daytime `11919-953-151 → 12619-953-151`. The W23/W24 hand
derivations and `weekday_night == 151` are still correct and need no change.
Alternatively, adopt `audit/test_characterization.py` (which re-pins all of
this against the current CSV) as the real-log suite of record and strip the
real-log tests from the engine's own files. Either way, consider narrowing the
deny rule to `engine_v2/afc_hours/**` so tests can track data.

---

## 2. Findings in the engine code

### F2 — LOW: `Minutes = inf` crashes ingest with an uncaught OverflowError

`core.py:310`: `provided = int(round(float(mv)))` guarded only by
`except ValueError`. `float("inf")` parses, `int(inf)` raises **OverflowError**,
which escapes as a raw traceback with no row number — the only malformed input
that doesn't die with a clean, row-numbered message. (`"nan"` happens to be
caught because `int(float("nan"))` raises ValueError.) Reproduced:
`OverflowError: cannot convert float infinity to integer`.

```diff
-                    try:
-                        provided = int(round(float(mv)))
-                    except ValueError:
-                        provided = None
+                    try:
+                        provided = int(round(float(mv)))
+                    except (ValueError, OverflowError):
+                        provided = None
```

Payroll impact: none (crash, not a wrong number). Pinned as
`test_defect_minutes_inf_crashes_with_overflowerror`.

### F3 — LOW: the invariant net misses duplicates that fit within the day span

I6 (`core.py:494`) checks _worked minutes ≤ clock span_ per day. That catches a
plain duplicated period (worked > span) — the case
`test_i6_catches_overlap_passed_directly_to_compute` pins — but not a duplicate
padded by a long enough gap. Feeding `compute()` directly (bypassing ingest):

```
09:00–10:00, 09:00–10:00 (duplicate), 11:00–23:00
→ worked 840 = span 840 → all six invariants PASS, total double-counts 60 min
```

`ingest_csv()` rejects this (its overlap guard is sound — proof in §4), so the
CSV pipeline is safe; the gap only matters for direct programmatic callers such
as the future `money.py`, which per the architecture consumes `core`'s result.
Since I6's stated purpose is exactly "catches overlap/duplicate rows that
slipped past ingest", it should check pairwise non-overlap per day, which is
strictly stronger and just as cheap:

```diff
-    # I6 per-day worked minutes cannot exceed the clock span (...)
-    span = all(r.duration_min <= r.end_min - r.start_min for r in days)
+    # I6 per-day raw periods must not overlap (catches overlap/duplicate rows
+    # that slipped past ingest, e.g. if compute() is called with raw rows)
+    by_day: dict = {}
+    for r in raw_rows:
+        by_day.setdefault(r.date, []).append(r)
+    span = all(a.end_min <= b.start_min
+               for rs in by_day.values()
+               for a, b in zip(*(lambda s: (s, s[1:]))(
+                   sorted(rs, key=lambda r: (r.start_min, r.end_min)))))
```

(`_check_invariants` would need the raw rows passed in; the current span check
can be kept as well.) Payroll impact today: none — the only entry point in use
is the CSV. Pinned as `test_defect_i6_misses_duplicate_that_fits_within_span`.

### F4 — INFO: `Minutes` cross-check has silent paths

Two behaviours diverge from the spirit of AUDIT_BRIEF §1.5 ("a row that
disagrees … is recorded as a non-fatal warning"):

- A **non-numeric** value (`abc`) is silently treated as absent — no warning —
  while a numeric mismatch warns. A typo'd column silently loses its
  cross-check. (`core.py:308-312`)
- A **fractional** value is rounded before comparison: `537.4` against a true
  537 rounds to 537 → **no warning**, while `537.6` → 538 → warns. Sub-half-
  minute discrepancies are invisible; also inconsistent with the engine's own
  "non-zero seconds are rejected, never truncated" stance on times.

Recommended: warn on unparseable values, and compare the raw float against the
recomputed integer (`float(mv) != duration`) instead of comparing after
rounding. Payroll impact: none — the recomputed value is always authoritative;
only the advisory warning channel is lossy. Pinned as
`test_defect_non_numeric_minutes_silently_ignored` and
`test_defect_fractional_minutes_rounding_masks_mismatch`.

### F5 — INFO (doc): two-digit month-name years are accepted but undocumented

`_MONTH_FORMATS` (`core.py:210`) includes `%d-%b-%y`; the real CSV relies on it
(`1-Jun-26`). AUDIT_BRIEF §1.2 documents only 4-digit forms. Not a bug — CPython's
`%Y` requires exactly 4 digits so there is no `26 → year 0026` ambiguity
(verified), and an out-of-window `1-Jun-99` → 1999 dies at the year guard — but
brief and code should agree. Pinned as
`test_two_digit_year_month_name_dates_accepted`.

### F6 — INFO (documented behaviour): the overnight split drops one minute

The `End precedes Start` error (`core.py:299-304`) instructs: split an
overnight shift into a row ending 23:59 and one starting 00:00. That structurally
un-records the 23:59→00:00 minute. Deliberate and worker-adverse (never
inflates a claim), so payroll-safe — but it should be stated in the brief and
in any user-facing instructions, since each overnight shift permanently
under-counts by one minute.

---

## 3. Current-data verification (independent re-derivation)

Hand-summed from `data/filipe_working_hours_log.csv` (22 rows, 1–26 Jun 2026),
then compared with the engine and with the committed `web_data.json`:

| Week      | Days          | Hand-summed total                   | Bands (contracted / additional / overtime) |
| --------- | ------------- | ----------------------------------- | ------------------------------------------ |
| 2026-W23  | 1–7 Jun (6)   | 537+535+772+794+360+409 = **3 407** | 1350 / 900 / 1 157                         |
| 2026-W24  | 8–14 Jun (6)  | 624+665+539+609+417+544 = **3 398** | 1350 / 900 / 1 148                         |
| 2026-W25  | 15–19 Jun (5) | 579+554+516+527+379 = **2 555**     | 1350 / 900 / 305                           |
| 2026-W26  | 22–26 Jun (5) | 586+642+757+574+700 = **3 259**     | 1350 / 900 / 1 009                         |
| **Total** | 22            | **12 619** (210.32 h)               | **5 400 / 3 600 / 3 619**                  |

Classes: weekday_night = 54 (3 Jun) + 79 (4 Jun) + 18 (24 Jun) = **151**;
sunday = 409 + 544 = **953**; saturday = bank_holiday = 0; daytime = **11 515**.
`unsocial_within_baseline = 0` (every Sunday/evening falls after its week's
1 350-minute baseline). All six integrity flags true; no warnings. The engine
agrees on every figure, and `emit`'s output for this input is byte-identical to
the committed `web_data.json` content block.

## 4. Behaviours verified correct (with the two non-obvious proofs)

- **Threshold banding** at, below, between and above 1350/2250; mid-period
  straddles split at the exact minute (e.g. Wed 08:00–18:00 after 1 200 min
  splits at 10:30); row order cannot affect results (`band_week` sorts
  temporally; verified by reversing the real log — identical totals and
  segments).
- **Clock boundaries.** Day window is [06:00, 20:00): 19:59–20:00 → daytime,
  20:00–20:01 → night, 05:59–06:00 → night, 06:00–06:01 → daytime;
  00:00–23:59 → 840 day + 599 night. _Soundness of classifying each piece by
  its start (`core.py:376`):_ `clock_segments` cuts at every boundary strictly
  inside the interval, so no resulting piece contains a boundary in its
  interior — each piece lies wholly in one window, and its start determines
  that window.
- **Overlap rejection adjacency argument (`core.py:319-340`).** Periods are
  sorted by (start, end) and only consecutive pairs are compared. Sufficient:
  if no adjacent pair overlaps, then `end_k ≤ start_(k+1)` for every k, and
  since every period has positive length (zero-length is rejected earlier),
  `end_i ≤ start_(i+1) < end_(i+1) ≤ … ≤ start_j` for any i < j — so no
  non-adjacent pair can overlap either. Contained periods sort adjacent to
  their container and are caught (existing test confirms).
- **Day types.** Bank holiday beats weekday (31 Aug 2026) and never collides
  with weekends (the rules table stores observed substitute dates only —
  2027-12-25 is plain Saturday; 2027-12-27/28 are bank holidays). The 2026/2027
  tables match gov.uk England & Wales (8 per year, weekdays all correct —
  re-checked date by date).
- **Pay-week grouping.** `week_anchor` modulo arithmetic correct for all seven
  weekdays; Sunday and the following Monday land in different weeks; gap weeks
  don't inflate `week_count` or the per-week mean; a partial first week bands
  from zero.
- **Within-baseline flag** fires only for unsocial minutes before the 1 350th
  of their week (mixed-week case: a Monday-evening 60 night minutes flagged, a
  post-baseline Sunday not).
- **Ingest guards.** All §3.7 malformed inputs die with row-numbered errors
  (overnight, zero-length, ambiguous/dotted/unknown dates, bad times, non-zero
  seconds, year guard, missing fields/columns, empty input); BOM handled;
  blank lines skipped; contiguous and split shifts accepted.
- **Statistics** use recorded-day/week denominators, floats appear only in
  presentational fields, single-day datasets behave, percentages reconcile.
- **Determinism.** Same CSV → identical `HoursResult` and identical `content`
  bytes; only `meta.generated_at` varies, and it is injectable.

## 5. Scope

Engine (Part i) only. `money.py` (Part ii) does not exist; the website is out of
scope; no file under `engine_v2/` was modified (the deny rule was honoured —
all patches above are proposals). Open decision for Filipe: apply F1's test
fix (or adopt `audit/` as the suite of record), and optionally F2–F4.
