# Plan: Website v1 components (useHoursData + six panels)

STATUS: EXECUTED 2026-07-19 — scaffold committed as c16bb77, components as
e9eb01d, deployed live to GitHub Pages the same day. Kept for the work-audit
trail; the next slice (v1.1 / improvements) needs a fresh plan.

## Success criteria

1. `useHoursData` composable: fetches `${import.meta.env.BASE_URL}web_data.json`
   on mount; gates on schema ≥ 1.1.0 (1.x with minor ≥ 1; anything else → a
   visible error state, no partial render); exposes typed
   `{ data, loading, error }`. No retries, no caching cleverness.
2. Six presentational components, wired into App.vue in §3 order:
   SummaryHeader, TotalsPanel, WeeklyTable, DailyTable, MethodologyPanel,
   IntegrityPanel. All figures come from the JSON; the only conversions are
   `format.ts` calls (durations → minutesToHours; clocks → minuteToClock;
   counts raw; percentages with %).
3. **DECIDED 2026-07-19 (user): option a now, c later.** The audience is a
   non-technical payroll reader; presentation clarity supersedes strict
   zero-calculation. Restated principle: the ENGINE determines every hours
   figure; the browser only re-presents them — unit conversion, labels, and
   sums of already-computed minute values, all confined to `lib/format.ts`
   (`sumMinutes`); the browser never classifies, bands, or produces a figure
   the engine could disagree with. At the next deliberate engine lock-lift
   (schema 1.2.0), `above_contract_minutes` moves into the emitted JSON and
   the format.ts sum is deleted (parked in docs/TODO.md).
4. Styling per §5: white background, NHS-blue accent (#005EB8) on near-black
   text, tabular numerals (`tabular-nums`) for all figures, hairline table
   borders, semantic `<table>` markup, WCAG-AA contrast, responsive to mobile,
   no external fonts/trackers/libraries beyond what is already installed.
5. Identity-light: `meta.subject` rendered only if present (it is absent);
   generic label otherwise. Weekly table surfaces
   `unsocial_within_baseline_minutes` and any `flagged_segments` (all 0/empty
   in current data, so also add an "if non-zero" visual affordance that we can
   only verify with a hand-crafted dev JSON).
6. No engine_v2 changes; no deploy artefacts (deploy stays blocked on §7).

## Steps

1. `src/composables/useHoursData.ts` (schema gate per BUILD_NOTES §4).
2. Components one at a time, §3 order, each consuming typed props.
3. Wire into App.vue; loading and error states visible.
4. Hand-crafted `dev-fixtures/bad-schema.json` + a temporary check that the
   gate rejects 1.0.0 (verified via curl/preview, not committed to public/).

## Verification

- `npx vue-tsc --noEmit` clean; `npm run build` passes.
- `vite preview` + curl: page HTML contains the exact expected strings
  ("280.13", "16808"-derived hours, period 2026-06-01 → 2026-07-14, six green
  integrity ticks, no "subject", no "£").
- Grep audit: `/ 60` appears only in `src/lib/format.ts`.
- Schema gate check: serving the bad-schema fixture produces the error state.
- Screenshot (or user eyeball via `npm run dev`) for the §5 design register —
  final look sign-off is the user's.
