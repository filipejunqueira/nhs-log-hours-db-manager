# audit/ — characterisation tests for the locked hours engine

This directory holds the test suite produced by the 2026-07-06 logic audit of
`engine_v2/` (report: `/docs/logic-audit_2026-07-06.md`).

It lives **outside** `engine_v2/` deliberately: the engine is complete, audited
and locked (`Edit`/`Write` under `engine_v2/**` are denied in
`.claude/settings.json`, and CLAUDE.md forbids modifying it). This suite imports
the package read-only and never writes inside it.

What it pins:

- The **frozen fixture** `engine_v2/tests/fixtures/hours_2026-07-14.csv`
  (32 rows, 1 Jun – 14 Jul 2026): grand totals, hand-derived weekly totals and
  bands, unsocial-class totals, integrity flags, cumulative series, row-order
  invariance, and emit determinism.

  **Frozen, not live, and deliberately so.** Pinning the working log would make
  these checks fail every time a day is added, which is noise rather than
  signal — the suite exists to catch a change in the *engine*, not a change in
  the data. Demonstrated 2026-08-18: the log grew from 47 to 58 days and all 29
  checks stayed green. `AFC_REAL_LOG` overrides the path if you deliberately
  want to run them against something else.

  (This paragraph previously described the suite as pinning the current real
  log at 22 days, and carried finding F1 as open. Both were wrong: F1 was
  fixed 2026-07-19, and the suite has always read the fixture. Corrected
  2026-08-19 by the full review.)
- AUDIT_BRIEF §3 scenarios the engine's 67 checks don't cover: threshold
  straddles inside one period, one-minute clock-boundary segments, the maximal
  00:00–23:59 day, 2027 substitute bank holidays, weekend/bank-holiday
  adjacency, pay-week edges, gap weeks, the mixed within-baseline week, BOM
  files, and more.
- The four checks for defects D1, D2, D2b and D3 from the report. **All four
  defects were FIXED on 2026-07-19**, and these tests were rewritten at that
  point to pin the *corrected* behaviour — which is why their names end
  `_after_f2`, `_after_f4` and `_after_f3`. They now fail if a fix is ever
  undone, rather than if one is applied.

  (This entry previously said they pin *defective* behaviour that "passes
  today" and would fail once a fix landed. That was true when written and has
  been inverted since the July fixes. Corrected 2026-08-19 by the full review.)

Run:

```
python3 audit/test_characterization.py   # standalone, stdlib only
pytest audit/                            # or under pytest
```

`AFC_REAL_LOG` overrides the real-log path, same as the engine's own tests.
