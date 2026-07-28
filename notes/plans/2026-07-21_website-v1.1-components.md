# Plan: Website v1.1 components (cross-tab, cumulative chart, stats panel)

STATUS: EXECUTED 2026-07-21 — all three components built, wired, and verified
(vue-tsc clean, build passes, grep audit clean, headless-browser render
cross-checked against raw JSON, user eyeballed the screenshot). The previous
plan (v1 six panels) is archived at
notes/plans/2026-07-19_website-v1-components.md; this one archives at the
next session wrap-up.

## Context

WEBSITE_PLAN §4 marks cross-tab, cumulative-trend-chart, and stats/distribution
as the v1.1 slice: all three read fields already present in the live
engine_v2/web_data.json (schema 1.1.0) — `content.cross_tab`,
`content.cumulative`, `content.statistics` — so this is purely additive, no
engine change. It is the top "Now" item in docs/TODO.md. v1 (six panels) is
live and verified on GitHub Pages.

Two decisions were open and are now resolved by the user (2026-07-21):
- **Charting**: Chart.js (not a hand-rolled SVG). This is a new dependency —
  the first non-Vue/Tailwind/Vite dependency in `website/`.
- **Test-claim gap**: docs/TODO.md's 2026-07-19 Done-log entry claims
  useHoursData's schema gate was "unit-tested 11 cases," but no test
  framework or test file exists anywhere in `website/` (confirmed via grep/
  find — no vitest, no `@vue/test-utils`, no `*.spec.*`/`*.test.*` files).
  Actual verification was manual (`vite preview` + curl against a
  hand-crafted bad-schema fixture, per plan.md's own v1 verification section).
  Decision: leave a note for later, do not fix the wording or add tests now.

## Success criteria

1. Three new presentational components, each following the existing pattern
   (single `defineProps<{ data: WebData }>()`, `<script setup lang="ts">`, no
   shared base component, importing only the specific `format.ts` helpers
   used):
   - **`CrossTab.vue`** — band × unsocial-class matrix from
     `content.cross_tab: Record<Band, ByClass>`. All cell values are
     durations → `minutesToHours`. Rows = bands, columns = classes,
     `labelForBand`/`labelForClass` for headers. No totals row/column added
     (WEBSITE_PLAN §4 says "a small matrix"; keeping v1.1 minimal per its own
     "start minimal" instruction — trivial to add later if wanted).
   - **`CumulativeChart.vue`** — line chart of `content.cumulative`
     (`{date, cumulative_minutes}[]`, 32 points, pre-computed, monotonic)
     via **chart.js + vue-chartjs** (the official Vue 3 wrapper — avoids
     hand-written canvas/lifecycle boilerplate; still "Chart.js" per your
     decision, just without re-deriving mount/unmount/resize handling by
     hand). The component passes the raw `cumulative_minutes` values to
     Chart.js for plotting; the only browser-side conversion is
     `minutesToHours` for axis/tooltip labels. No client-side recomputation
     of the running total, no re-sorting, no interpolation of missing dates.
   - **`StatsPanel.vue`** — `content.statistics`, applying the BUILD_NOTES §3
     field→formatter map exactly, including its two named traps:
     - `pct_by_band` / `pct_by_class` — already percentages, append `%`, no
       division.
     - `mean_minutes_per_day` / `mean_minutes_per_week` — durations →
       `minutesToHours`.
     - `mean_start_minute` / `mean_end_minute` — **clocks, not durations** →
       `minuteToClock`, despite the "mean_minutes"-adjacent naming.
     - `longest_day` / `shortest_day` — date + `minutesToHours`.
     - `days_touching_class` — **raw counts, not minutes** → render as-is,
       despite sharing the `ByClass` shape with the minute blocks.
2. Wired into `App.vue` as new siblings after the existing six panels, in the
   order WEBSITE_PLAN §10 step 9 gives: cross-tab, chart, stats.
3. `chart.js` + `vue-chartjs` added to `website/package.json` — the only new
   dependencies. No other new dependencies.
4. No change to `useHoursData`, any existing `format.ts` export,
   `types/web-data.ts`, or any v1 component — purely additive.
5. No `engine_v2` change; no change to `public/web_data.json` contents
   (fields already present at schema 1.1.0).
6. `docs/TODO.md` gets one added line, in Later/parked: a note that the
   2026-07-19 "unit-tested 11 cases" Done-log claim is unverified against
   the actual codebase (no test framework present) and should be reconciled
   (reworded or backed with real tests) later — explicitly out of scope here.
7. **Website app version** (added 2026-07-21, user request): a version
   number for the *website app* itself — distinct from and unrelated to the
   engine's locked `schema_version` (currently 1.1.0 in web_data.json, never
   touched here). `website/package.json` `"version"` bumped from the untouched
   Vite-scaffold default `"0.0.0"` to `"1.2.0"`. Single source of truth:
   `vite.config.ts` reads it from `package.json` and injects it as a build-time
   constant (`__APP_VERSION__`); no duplicated version string anywhere.
8. **Version footnote** (same request): a small `<footer>` in `App.vue`
   showing "Website v1.2.0" — muted text, consistent with the existing design
   register (no new colours/fonts/trackers). Purely a label; not derived from
   or interacting with any hours figure.

## Steps

1. `npm install chart.js vue-chartjs` in `website/`.
2. `CrossTab.vue` — semantic `<table>`/`<caption>`, `tabular-nums` on cells,
   consistent with existing panel styling.
3. `CumulativeChart.vue` — `<Line>` component from vue-chartjs bound to a
   dataset built from `content.cumulative`; y-axis/tooltip callback formats
   via `minutesToHours`.
4. `StatsPanel.vue` — table/definition-list consistent with existing panels,
   the field→formatter map applied per success criterion 1.
5. Wire all three into `App.vue` after `IntegrityPanel`, in cross-tab →
   chart → stats order.
6. Add the one-line note to `docs/TODO.md` Later/parked (success criterion 6).
7. Bump `website/package.json` version to `1.2.0`; wire `vite.config.ts` to
   read it and `define` `__APP_VERSION__`; add the ambient type declaration.
8. Add the version footer to `App.vue`.

## Verification

- `npx vue-tsc --noEmit` clean; `npm run build` passes (run from `website/`).
- Grep audit: minute-arithmetic (`/ 60`, etc.) still appears only in
  `src/lib/format.ts` — the new components call existing format.ts exports,
  they don't inline conversions.
- Manual check against raw `web_data.json`: `mean_start_minute` /
  `mean_end_minute` render as HH:MM (not decimal hours); `days_touching_class`
  renders as plain integers (not hours) — the two BUILD_NOTES §3 traps.
- `vite preview` + eyeball: cross-tab matrix values are consistent with
  `content.totals.minutes_by_band` / `minutes_by_class` sums (checked by eye,
  not computed in-app); chart renders 32 points ending at 16 808 min /
  280.13 h; stats panel percentages are sane (~100% within band, ~100%
  within class).
- User eyeball via `npm run dev` for the chart's visual look and overall
  page composition — final sign-off is the user's, per project convention.
