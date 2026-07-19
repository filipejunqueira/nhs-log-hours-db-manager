# Plan: Scaffold `website/` — Vite + Vue 3 + TS + Tailwind v4

## Context

The repo has a locked Python engine (`engine_v2/`) that emits `web_data.json`
(schema 1.1.0, current totals: 16808 min / 280.13 h). The next step per
WEBSITE_PLAN.md §10 is to scaffold the Vue front-end that will render that JSON.
This plan covers **scaffolding only** — no components, no composable, no
deployment wiring yet.

BUILD_NOTES.md corrects the plan in several ways that apply here:
- **Tailwind v4** (not v3): no `tailwind.config.js`, no `postcss.config.js`.
  Use `@tailwindcss/vite` plugin + `@import "tailwindcss"` in CSS.
- Schema gate must be **≥ 1.1.0**, not just "starts with 1.".
- Field→formatter map (§3 of BUILD_NOTES) governs what goes in `format.ts`.

---

## Steps

### 1. Scaffold with Vite

```bash
cd /home/filipejunqueira/code/nhs-hour-log
npm create vite@latest website -- --template vue-ts
```

This creates `website/` with `package.json`, `vite.config.ts`, `tsconfig*.json`,
`index.html`, `src/main.ts`, `src/App.vue`, `src/style.css`, etc.

### 2. Install dependencies

```bash
cd website
npm install
npm install tailwindcss @tailwindcss/vite
```

### 3. Wire Tailwind v4 into Vite

**`website/vite.config.ts`** — add `tailwindcss()` plugin and set `base`:

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  base: '/nhs-hour-log/',
  plugins: [
    vue(),
    tailwindcss(),
  ],
})
```

**`website/src/style.css`** — replace contents with:

```css
@import "tailwindcss";
```

Ensure `src/main.ts` imports `./style.css` (Vite's vue-ts template already does
this).

**Delete** any `tailwind.config.js` or `postcss.config.js` if the scaffold
created them (it shouldn't for a vue-ts template, but guard against it).

### 4. Create `src/types/web-data.ts`

Stub file with the TypeScript types from WEBSITE_PLAN.md §2, **bound to the
real emitted JSON shape** (BUILD_NOTES §3: "bind TS types to the REAL emitted
web_data.json; it wins over the §2 sketch if they differ"). After reading the
actual JSON, the §2 types match — no discrepancies found.

Contents:

```ts
// Types mirroring engine_v2/web_data.json (schema 1.1.0).
// Source of truth is the engine output; these track it.

export type Band = "contracted" | "additional" | "overtime"
export type UnsocialClass = "daytime" | "weekday_night" | "saturday" | "sunday" | "bank_holiday"
export type DayTypeName = "weekday" | "saturday" | "sunday" | "bank_holiday"
export type ByBand = Record<Band, number>
export type ByClass = Record<UnsocialClass, number>

export interface Meta {
  schema_version: string
  generated_at: string
  unit: "minutes"
  unit_note: string
  contract: {
    contracted_weekly_minutes: number
    fulltime_weekly_minutes: number
    pay_week_start: string
  }
  rules: {
    day_window_start_minute: number
    night_window_start_minute: number
    weekend_and_bankhol_whole_day: boolean
    bank_holidays: string[]
    bank_holiday_years_covered: number[]
  }
  methodology: string[]
  subject?: { name?: string; post?: string; [k: string]: unknown }
}

export interface FlaggedSegment {
  date: string
  start_minute: number
  end_minute: number
  duration_minutes: number
  unsocial_class: UnsocialClass
}

export interface WeekSummary {
  iso_week: string
  monday: string
  day_count: number
  total_minutes: number
  minutes_by_band: ByBand
  minutes_by_class: ByClass
  unsocial_within_baseline_minutes: number
  flagged_segments: FlaggedSegment[]
}

export interface DayRecord {
  date: string
  iso_weekday: number
  day_type: DayTypeName
  start_minute: number
  end_minute: number
  duration_minutes: number
  minutes_by_class: ByClass
}

export interface Integrity {
  conservation_ok: boolean
  partitions_ok: boolean
  uniqueness_ok: boolean
  banding_formula_ok: boolean
  crosstab_ok: boolean
  span_ok: boolean
  total_raw_minutes: number
  total_segment_minutes: number
  unsocial_within_baseline_minutes: number
  warnings: string[]
}

export interface WebData {
  meta: Meta
  content: {
    period: { start: string; end: string }
    totals: {
      total_minutes: number
      day_count: number
      week_count: number
      minutes_by_band: ByBand
      minutes_by_class: ByClass
      unsocial_within_baseline_minutes: number
    }
    weekly: WeekSummary[]
    daily: DayRecord[]
    cross_tab: Record<Band, ByClass>
    cumulative: { date: string; cumulative_minutes: number }[]
    statistics: {
      pct_by_band: ByBand
      pct_by_class: ByClass
      mean_minutes_per_day: number
      mean_minutes_per_week: number
      mean_start_minute: number
      mean_end_minute: number
      longest_day: { date: string; minutes: number }
      shortest_day: { date: string; minutes: number }
      days_touching_class: ByClass
    }
    integrity: Integrity
  }
}
```

### 5. Create `src/lib/format.ts`

The **only** place browser arithmetic happens. Follows the field→formatter map
from BUILD_NOTES §3:

```ts
// The ONLY arithmetic the front end performs: minutes ÷ 60 for display.

/** Duration in minutes → "X.XX" hours string (2 dp). */
export function minutesToHours(min: number): string {
  return (min / 60).toFixed(2)
}

/** Minutes-from-midnight → "HH:MM" clock string. */
export function minuteToClock(min: number): string {
  const h = Math.floor(min / 60)
  const m = min % 60
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`
}

/** Human-readable label for a Band key. */
export function labelForBand(band: string): string {
  const labels: Record<string, string> = {
    contracted: "Contracted",
    additional: "Additional",
    overtime: "Overtime",
  }
  return labels[band] ?? band
}

/** Human-readable label for an UnsocialClass key. */
export function labelForClass(cls: string): string {
  const labels: Record<string, string> = {
    daytime: "Daytime",
    weekday_night: "Weekday Night",
    saturday: "Saturday",
    sunday: "Sunday",
    bank_holiday: "Bank Holiday",
  }
  return labels[cls] ?? cls
}
```

### 6. Copy `web_data.json` into `website/public/`

```bash
cp engine_v2/web_data.json website/public/web_data.json
```

This lets `npm run dev` serve the real data at runtime.

### 7. Clean up scaffolding boilerplate

- Strip Vite's default `HelloWorld.vue` component and counter example from
  `App.vue`. Replace with a minimal placeholder that confirms the app loads
  (e.g. `<h1>NHS Hours Dashboard</h1>`).
- Remove `src/components/HelloWorld.vue` and any other template files.
- Remove Vite/Vue logo SVGs from `src/assets/` and `public/`.

### 8. Verify

```bash
cd website && npm run dev   # should serve on localhost, show the placeholder
npx vue-tsc --noEmit        # types compile cleanly
```

---

## Files created/modified

| File | Action |
|------|--------|
| `website/` (entire scaffold) | **created** by `npm create vite` |
| `website/vite.config.ts` | **edited**: add `tailwindcss()` plugin, set `base: '/nhs-hour-log/'` |
| `website/src/style.css` | **edited**: replace with `@import "tailwindcss"` |
| `website/src/types/web-data.ts` | **created**: TypeScript types matching schema 1.1.0 |
| `website/src/lib/format.ts` | **created**: four formatting functions (the only converters) |
| `website/public/web_data.json` | **copied** from `engine_v2/web_data.json` |
| `website/src/App.vue` | **edited**: minimal placeholder, remove boilerplate |
| `website/src/components/HelloWorld.vue` | **deleted** |
| `tailwind.config.js`, `postcss.config.js` | **deleted** if they exist |

## Files NOT touched

- `engine_v2/` — locked, read-only.
- `docs/`, `scripts/`, `CLAUDE.md` — no changes needed for scaffolding.

---

## Verification (post-implementation)

1. `npm run dev` serves at `http://localhost:5173/nhs-hour-log/` and shows
   the placeholder heading.
2. `npx vue-tsc --noEmit` passes — types compile with no errors.
3. `web_data.json` is fetchable at
   `http://localhost:5173/nhs-hour-log/web_data.json`.
4. Check the real data: total_minutes is 16808 (280.13 h), all six integrity
   flags are `true`, bands sum to total (8528 + 4540 + 3740 = 16808), classes
   sum to total (15704 + 151 + 0 + 953 + 0 = 16808).
   (Figures refreshed 2026-07-19 after the 07-18 dataset adoption; the plan
   originally cited the 22-day June snapshot.)
5. No `tailwind.config.js` or `postcss.config.js` in the tree.
