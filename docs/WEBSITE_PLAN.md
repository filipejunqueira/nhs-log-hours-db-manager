# NHS Hours Dashboard — Planning & Repository Structure

Rough plan for the public dashboard that renders the hours engine's output. Written
for a Claude Code session building the site. Decisions already settled in earlier
work are marked **[settled]**; things still needing your input are marked
**[YOUR DECISION]**.

---

## 1. Purpose & hard principles

The site renders `web_data.json` (produced by the Python engine in `engine_v2/`)
as a clean, legible dashboard of working hours. It exists so that the worker's
extra hours are transparent and a payroll reader can apply whatever enhancements
are appropriate, **without the page telling them what rates to use**.

Non-negotiable principles (these shaped the engine and must hold in the site):

1. **The front end does zero calculation.** Every figure comes pre-computed from
   the JSON. The *only* arithmetic permitted in the browser is dividing minutes by
   60 for display, and formatting. No banding, no aggregation, no rates. **[settled]**
2. **Minutes are the source of truth; hours are display only.** The JSON is in
   integer minutes. The UI shows hours (mins ÷ 60, 2 dp) for humans, but never
   feeds a rounded hour back into anything. **[settled]**
3. **No money, ever.** The JSON contains no monetary value; the site must not add
   one. It presents hours and the methodology; rates are "determined separately".
   **[settled]**
4. **Legible computation.** A reader must be able to see *how* the hours were
   computed (the methodology block) and that the figures are internally consistent
   (the integrity block), so they can trust and act on them. Make this obvious
   without leading the reader toward any particular pay conclusion. **[settled]**
5. **Privacy-minimal.** Render only what's needed. Name is optional (see §7).

---

## 2. Data contract (what the site consumes)

The site fetches one file: `web_data.json`, **schema 1.1.0**. The site must treat
this shape as the contract and bind TypeScript types to it. All `*_minutes` /
`*_minute` fields are integers (minutes). Do not assume any field is in hours.

Top level: `{ meta, content }`.

`meta`:
- `schema_version` (string) — gate the UI on the major version.
- `generated_at` (ISO 8601 string, UTC) — show as "last updated".
- `unit` = `"minutes"`, `unit_note` (string) — display the note somewhere.
- `contract`: `{ contracted_weekly_minutes: 1350, fulltime_weekly_minutes: 2250, pay_week_start: "monday" }`.
- `rules`: `{ day_window_start_minute, night_window_start_minute, weekend_and_bankhol_whole_day, bank_holidays: string[], bank_holiday_years_covered: number[] }`.
- `methodology`: `string[]` — render verbatim, in order. This is the "how hours are computed" panel.
- `subject` (optional): `{ name?, post?, ... }` — present only if injected at build/deploy. Absent by default.

`content`:
- `period`: `{ start, end }` (ISO dates).
- `totals`: `{ total_minutes, day_count, week_count, minutes_by_band, minutes_by_class, unsocial_within_baseline_minutes }`.
- `weekly`: array of `{ iso_week, monday, day_count, total_minutes, minutes_by_band, minutes_by_class, unsocial_within_baseline_minutes, flagged_segments[] }`.
- `daily`: array of `{ date, iso_weekday, day_type, start_minute, end_minute, duration_minutes, minutes_by_class }`.
- `cross_tab`: `{ [band]: { [class]: minutes } }` — bands × unsocial classes (the rate-able pieces).
- `cumulative`: array of `{ date, cumulative_minutes }` — pre-computed trend series.
- `statistics`: `{ pct_by_band, pct_by_class, mean_minutes_per_day, mean_minutes_per_week, mean_start_minute, mean_end_minute, longest_day:{date,minutes}, shortest_day:{date,minutes}, days_touching_class }`.
- `integrity`: `{ conservation_ok, partitions_ok, uniqueness_ok, banding_formula_ok, crosstab_ok, span_ok, total_raw_minutes, total_segment_minutes, unsocial_within_baseline_minutes, warnings[] }`.

`minutes_by_band` keys: `contracted`, `additional`, `overtime`.
`minutes_by_class` keys: `daytime`, `weekday_night`, `saturday`, `sunday`, `bank_holiday`.

### TypeScript types (build these first, mirror the schema exactly)

```ts
type Band = "contracted" | "additional" | "overtime";
type UnsocialClass = "daytime" | "weekday_night" | "saturday" | "sunday" | "bank_holiday";
type DayTypeName = "weekday" | "saturday" | "sunday" | "bank_holiday";
type ByBand = Record<Band, number>;
type ByClass = Record<UnsocialClass, number>;

interface Meta {
  schema_version: string;
  generated_at: string;
  unit: "minutes";
  unit_note: string;
  contract: { contracted_weekly_minutes: number; fulltime_weekly_minutes: number; pay_week_start: string };
  rules: {
    day_window_start_minute: number; night_window_start_minute: number;
    weekend_and_bankhol_whole_day: boolean;
    bank_holidays: string[]; bank_holiday_years_covered: number[];
  };
  methodology: string[];
  subject?: { name?: string; post?: string; [k: string]: unknown };
}

interface FlaggedSegment { date: string; start_minute: number; end_minute: number; duration_minutes: number; unsocial_class: UnsocialClass; }
interface WeekSummary { iso_week: string; monday: string; day_count: number; total_minutes: number; minutes_by_band: ByBand; minutes_by_class: ByClass; unsocial_within_baseline_minutes: number; flagged_segments: FlaggedSegment[]; }
interface DayRecord { date: string; iso_weekday: number; day_type: DayTypeName; start_minute: number; end_minute: number; duration_minutes: number; minutes_by_class: ByClass; }
interface Integrity { conservation_ok: boolean; partitions_ok: boolean; uniqueness_ok: boolean; banding_formula_ok: boolean; crosstab_ok: boolean; span_ok: boolean; total_raw_minutes: number; total_segment_minutes: number; unsocial_within_baseline_minutes: number; warnings: string[]; }

interface WebData {
  meta: Meta;
  content: {
    period: { start: string; end: string };
    totals: { total_minutes: number; day_count: number; week_count: number; minutes_by_band: ByBand; minutes_by_class: ByClass; unsocial_within_baseline_minutes: number };
    weekly: WeekSummary[];
    daily: DayRecord[];
    cross_tab: Record<Band, ByClass>;
    cumulative: { date: string; cumulative_minutes: number }[];
    statistics: {
      pct_by_band: ByBand; pct_by_class: ByClass;
      mean_minutes_per_day: number; mean_minutes_per_week: number;
      mean_start_minute: number; mean_end_minute: number;
      longest_day: { date: string; minutes: number }; shortest_day: { date: string; minutes: number };
      days_touching_class: ByClass;
    };
    integrity: Integrity;
  };
}
```

A single shared formatting helper does all minute→display conversion:
`minutesToHours(min): string` (÷60, 2 dp), `minuteToClock(min): "HH:MM"`,
`labelForClass`, `labelForBand`. Nothing else converts.

---

## 3. Functionality — v1 (minimum genuinely useful)

Build these first, top to bottom of the page:

1. **Header / summary.** Title; `meta.subject.name`/`post` if present, else a
   generic label; period covered (`content.period`); "last updated"
   (`meta.generated_at`); headline totals: total hours, hours above contract
   (additional + overtime), days worked, weeks active.
2. **Totals panel.** Hours by band (contracted / additional / overtime) and hours
   by unsocial class (daytime / weekday night / Saturday / Sunday / bank holiday),
   as cards or a compact table.
3. **Weekly table.** One row per ISO week: total, contracted, additional,
   overtime, plus the unsocial split. This is the core payroll-facing view. Show
   `unsocial_within_baseline_minutes` per week (normally 0) and surface any
   `flagged_segments` if non-zero.
4. **Daily log table.** Date, weekday, start, end, hours, day-type. Scrollable.
5. **Methodology panel.** Render `meta.methodology` verbatim, in order. This is
   the legibility requirement — how hours are computed, stated plainly.
6. **Integrity panel.** The six checks (`conservation_ok` … `span_ok`) as
   computed green ticks, plus `unsocial_within_baseline_minutes` and any
   `warnings`. Frame as "these checks are computed by the engine on every run",
   not asserted by the page.

## 4. Functionality — v1.1+ (data already present, add later)

7. **Cross-tab** (band × unsocial class) — the rate-able pieces, a small matrix.
8. **Cumulative trend chart** — line chart from `content.cumulative` (pre-computed
   points; the chart just plots them). A lightweight lib (e.g. Chart.js or a tiny
   SVG) — no data processing in the browser.
9. **Distribution / stats** — `statistics` percentages and means.

Start minimal; the JSON carries everything, so these are additive.

---

## 5. Design direction [settled, confirm if you want a change]

Calm, professional, NHS-adjacent — the same register as the earlier hours report:
restrained palette (an NHS-blue accent on near-black text, white background),
clean typography, generous spacing, tabular numerals for all figures, hairline
table borders. Conventional and trustworthy over flashy; this is a record someone
in payroll reads, not a marketing page. Accessible: semantic tables, WCAG-AA
contrast, keyboard-navigable, responsive down to mobile. No trackers or analytics
(privacy).

---

## 6. Tech stack & build approach [settled]

- **Vue 3 + TypeScript + Tailwind CSS + Vite.** Scaffold with
  `npm create vite@latest website -- --template vue-ts`, then add Tailwind.
- **Runtime data load.** The app `fetch`es `web_data.json` from
  `${import.meta.env.BASE_URL}web_data.json` on mount, validates `schema_version`,
  and renders. No backend, no server.
- **One composable** (`useHoursData`) owns load + parse + expose typed `WebData`;
  components are presentational.
- **No state library needed** — a single fetched object passed down (or provided
  via `provide/inject`).

---

## 7. Privacy, identity & hosting [DECIDED 2026-07-19: public repo + public
Pages, identity-light JSON (no `subject`); accepted with the exposure
trade-offs below understood — see docs/BUILD_NOTES.md §1]

GitHub Pages on a public repo is **world-readable**. The dashboard will show your
working pattern and (optionally) your name and NHS employer. Decide before deploy:

- **Identity:** default is **identity-light** — render `meta.subject` only if it's
  present in the JSON, and keep `subject` out of the committed JSON unless you
  choose to add it. Recommended: inject name/post at deploy time, or omit entirely
  and keep the site about the hours.
- **Visibility:** options are (a) public repo + public Pages (free, world-readable);
  (b) private repo + Pages (needs a paid GitHub plan, restricts access);
  (c) public but unlisted/obscure URL (security-by-obscurity, weak). No default
  chosen — pick before the first deploy.

Until decided, build the site to run with **no `subject`** in the JSON.

---

## 8. Repository structure

Currently the repo has one folder (`engine_v2/`). Target structure:

```
nhs-hour-log/
├── README.md                     # repo overview, how the pieces fit, how to update
├── .gitignore
├── engine_v2/                    # Python hours engine (Part i) — BUILT & AUDITED, do not modify
│   ├── afc_hours/                # rules.py, core.py, emit.py, __init__.py
│   ├── tests/                    # test_rules/core/emit (67 checks)
│   ├── data/                     # source CSV(s) the engine reads
│   ├── AUDIT_BRIEF.md
│   └── web_data.json             # generated output (the website's data source)
│   # (money.py = Part ii, not yet built; lives here when it is)
│
├── website/                      # Vue + TS + Tailwind + Vite dashboard
│   ├── public/
│   │   └── web_data.json         # copied from engine output at update time; fetched at runtime
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── types/
│   │   │   └── web-data.ts        # the interfaces in §2
│   │   ├── composables/
│   │   │   └── useHoursData.ts    # load + parse + schema check
│   │   ├── lib/
│   │   │   └── format.ts          # minutesToHours / minuteToClock / labels (the ONLY converters)
│   │   └── components/
│   │       ├── SummaryHeader.vue
│   │       ├── TotalsPanel.vue
│   │       ├── WeeklyTable.vue
│   │       ├── DailyTable.vue
│   │       ├── MethodologyPanel.vue
│   │       ├── IntegrityPanel.vue
│   │       ├── CrossTab.vue          # v1.1
│   │       ├── CumulativeChart.vue   # v1.1
│   │       └── StatsPanel.vue        # v1.1
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts            # set `base` to the Pages sub-path (e.g. "/nhs-hour-log/")
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── scripts/                      # automation for the daily update
│   └── update.sh                 # xlsx → csv → run engine → copy web_data.json into website/public → git add/commit/push
│
├── .github/
│   └── workflows/
│       └── deploy.yml            # on push to main: build website, deploy dist/ to GitHub Pages
│
└── docs/
    ├── WEBSITE_PLAN.md           # this file
    └── CONTINUATION_PROMPT.md    # session handoff
```

Notes:
- **The engine output is the website's input.** `engine_v2/web_data.json` is the
  canonical artifact; `scripts/update.sh` copies it to `website/public/web_data.json`
  (the site serves and fetches from `public/`). Keep one canonical generator; don't
  hand-edit either copy.
- **`vite.config.ts` `base`** must match the Pages URL sub-path or assets 404.

---

## 9. Deployment & the daily update flow

Recommended (simple, single branch):

1. **Code changes** → push to `main` → GitHub Actions (`deploy.yml`) runs
   `npm ci && npm run build` in `website/` and deploys `website/dist/` to Pages.
2. **Daily data update** (your cron, ~midnight): export the Excel log to CSV →
   run the engine to regenerate `engine_v2/web_data.json` → copy it to
   `website/public/web_data.json` → `git commit && git push`. The same Action
   rebuilds and redeploys. A rebuild of this tiny app is a few seconds in CI, so a
   daily rebuild is fine; no separate data-only deploy mechanism is needed.

`scripts/update.sh` should do the export → engine → copy → commit → push chain so
the cron calls one script. (The xlsx→csv export step depends on how you export;
keep dates ISO `YYYY-MM-DD` or the engine will hard-error by design.)

---

## 10. Build order for the Claude Code session

1. Scaffold `website/` (Vite vue-ts), add Tailwind, set `base` in `vite.config.ts`.
2. Add `src/types/web-data.ts` (§2) and `src/lib/format.ts` (the only converters).
3. Add `useHoursData` composable: fetch `web_data.json`, check `schema_version`
   starts with `1.`, expose typed data + loading/error states.
4. Build v1 components in order (§3): summary, totals, weekly, daily, methodology,
   integrity. Wire into `App.vue`.
5. Copy a real `web_data.json` into `website/public/` for development.
6. Verify against the real data: totals 11919 min (≈198.65 h), bands
   5400/3600/2919, all integrity flags true, within-baseline 0.
7. Add `.github/workflows/deploy.yml` and `scripts/update.sh`.
8. Resolve §7 (identity/hosting) before the first public deploy.
9. v1.1 components (cross-tab, chart, stats) once v1 looks right.

Do **not** modify `engine_v2/` — it is complete and independently audited. Treat
its JSON output as a fixed contract.
