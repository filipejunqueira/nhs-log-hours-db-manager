# audit/ — characterisation tests for the locked hours engine

This directory holds the test suite produced by the 2026-07-06 logic audit of
`engine_v2/` (report: `/logic-audit_2026-07-06.md`).

It lives **outside** `engine_v2/` deliberately: the engine is complete, audited
and locked (`Edit`/`Write` under `engine_v2/**` are denied in
`.claude/settings.json`, and CLAUDE.md forbids modifying it). This suite imports
the package read-only and never writes inside it.

What it pins:

- The **current** real log (`engine_v2/data/filipe_working_hours_log.csv`,
  22 days, 1–26 Jun 2026): grand totals, hand-derived weekly totals and bands,
  unsocial-class totals, integrity flags, cumulative series, row-order
  invariance, and emit determinism. (The engine's own tests in
  `engine_v2/tests/` still pin the superseded 21-day snapshot and its renamed
  CSV — see report finding F1.)
- AUDIT_BRIEF §3 scenarios the engine's 67 checks don't cover: threshold
  straddles inside one period, one-minute clock-boundary segments, the maximal
  00:00–23:59 day, 2027 substitute bank holidays, weekend/bank-holiday
  adjacency, pay-week edges, gap weeks, the mixed within-baseline week, BOM
  files, and more.
- Tests named `test_defect_*` pin current **defective** behaviour documented in
  the report (D1–D3). They pass today; if a fix lands in the engine they fail,
  making the behaviour change deliberate and visible. Update both the test and
  the report when that happens.

Run:

```
python3 audit/test_characterisation.py   # standalone, stdlib only
pytest audit/                            # or under pytest
```

`AFC_REAL_LOG` overrides the real-log path, same as the engine's own tests.
