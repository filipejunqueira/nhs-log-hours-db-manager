# Plan: act on the v1.1 code-review findings

STATUS: EXECUTED 2026-07-28 — all seven changes made and verified (real type
check clean, build passes, grep audit clean, compile-time enforcement proven by
a deliberate break, three-fixture headless-browser check). The previous plan
(v1.1 components) is archived at
notes/plans/2026-07-21_website-v1.1-components.md; this one archives at the
next session wrap-up.

## Context

A code review of the v1.1 commit (6b98f8e) found six issues; all six were
checked against the source and all six were real.

The one that mattered: the page checked the **schema version** of
web_data.json and nothing else, and the band/class key names were written out
by hand in five separate places (three components plus the two label maps in
format.ts). Because the version gate accepts any 1.x with minor >= 1, a future
engine release adding a clock class would load fine and silently drop a
column — leaving the cross-tab rows no longer adding up to the totals printed
directly above them. Silently wrong numbers on a page whose whole purpose is
being checkable by payroll. The mirror failure: a missing block threw inside a
component and blanked the page instead of using the error panel App.vue
already had.

User decisions taken before execution (2026-07-28):
- Unrecognised keys → **render what is understood, warn visibly**. Explicitly
  NOT a hard refusal: a future engine release must not be able to take the
  live page down.
- All six findings in scope, nits included.
- Playwright → scratch install outside the repo again, not a dev dependency.
- No vitest, no test framework. That remains parked.

## Success criteria

1. Band and clock-class names exist in exactly one place, and the compiler
   rejects adding a key there without a display label. **Met** — proven by
   deliberately adding a fourth band: `vue-tsc -b` fails with TS2741.
2. Unrecognised band/class key → every recognised column still renders, above
   a visible warning naming the unrecognised one. **Met.**
3. A missing content block → the existing "could not load" panel, never a
   blank page. **Met.**
4. Real data → no banner, page unchanged from before. **Met.**
5. Percentage columns show a consistent number of decimals. **Met** —
   "0.90%" / "0.00%" where it previously read "0.9%" / "0%".
6. The running total is available to a screen reader. **Met** — sr-only
   summary; it appears in no table anywhere on the page.
7. `/ 60` appears only in src/lib/format.ts. **Met.**

## Changes

All under website/. No engine change; web_data.json contents untouched.

1. **src/lib/format.ts** — added `BANDS` and `CLASSES` const arrays as the
   single source of the key names. Label maps retyped as
   `Record<(typeof BANDS)[number], string>`, which is what makes criterion 1
   a compile error rather than a convention. Added `formatPercent` (no
   arithmetic — the engine already emits percentages) and
   `minutesToHoursValue` (minutes → hours as a number, for plotting only).
2. **src/types/web-data.ts** — `Band` / `UnsocialClass` now derive from those
   arrays via `import type`, so the module still emits no runtime JavaScript.
3. **TotalsPanel.vue, CrossTab.vue, StatsPanel.vue** — dropped their local
   copies of the arrays; import `BANDS` / `CLASSES` instead.
4. **src/lib/validate.ts** (new) — `checkData` returns `{ fatal, warnings }`.
   Fatal: any of period/totals/weekly/daily/cross_tab/cumulative/statistics/
   integrity absent. Warnings: band or class keys present in the data but not
   in BANDS/CLASSES, or expected keys absent.
5. **useHoursData.ts / App.vue** — the check runs after the version gate; a
   fatal result throws into the existing error panel, warnings surface as a
   new amber banner above the page.
6. **StatsPanel.vue** — the two share columns go through `formatPercent`.
7. **CumulativeChart.vue** — plots hours rather than minutes, so Chart.js
   picks round-hour ticks (the axis read 33.33 h / 66.67 h before, and 33 h /
   67 h when only the label was rounded; it now reads 0/50/100/…/300 h).
   Tooltip still formats from the original minutes via `minutesToHours`, so
   the exact figure comes from format.ts. Added the sr-only summary. Moved
   the props read inside the `computed`, which previously could never
   recompute — the snapshot pattern in the other eight components is
   deliberate and untouched.
8. **package.json 1.2.0 → 1.3.0** (behaviour changed: the new banner), and
   package-lock.json's two root `"version"` fields hand-edited to match.
   Deliberately not `npm install`, which would re-resolve the caret ranges
   and could pull dependency updates into a deployed site as a side effect of
   a cosmetic fix.

## Verification

Run from website/ — the shell working directory resets between commands here,
so use an explicit cd every time.

- `npx vue-tsc -b --force` — clean. **Note: `npx vue-tsc --noEmit` checks zero
  files** in this project, because the root tsconfig.json is a references-only
  solution file (`"files": []`). It always exits 0 and proves nothing. The
  real check is `-b`, which is what `npm run build` runs.
- `npm run build` — passes.
- `grep -rn "/ 60" src/` — hits only in src/lib/format.ts. Also checked that
  no `toFixed` appears outside format.ts.
- Deliberate break: adding a fourth band to `BANDS` without a label fails
  `vue-tsc -b` with TS2741. Restored afterwards.
- Headless browser (scratch Playwright install outside the repo) against three
  data files served through `vite preview`, checking the rendered DOM:
  - real data → no banner, no error panel, footer "Website v1.3.0", shares
    read 50.74/27.01/22.25 and 93.43/0.90/0.00/5.67/0.00, days-touching still
    plain integers 30/3/0/2/0, mean start 08:31 / end 17:16, no page errors;
  - a fixture with an extra "night_premium" clock class → banner names it, all
    recognised columns still render, no page errors;
  - a fixture with the statistics block deleted → error panel with a message
    naming the missing block, not a blank page.
  Fixtures lived outside the repo; dist/web_data.json restored afterwards and
  confirmed identical to public/web_data.json.
- User eyeball on the chart axis and banner styling.
