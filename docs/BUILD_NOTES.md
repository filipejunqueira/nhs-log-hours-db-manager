# Build Notes — corrections & clarifications to WEBSITE_PLAN.md

Date: 2026-06-26. These supersede WEBSITE_PLAN.md where they conflict.

## 1. Visibility decision is the real blocker (patches §7)
§7 frames privacy as "show the name or not". The larger exposure is the dataset itself:
web_data.json contains every worked date, start/end time, and weekly pattern, and on a public
repo the commit history timestamps each daily update. "Identity-light" removes the name but
leaves a complete behavioural record of an identifiable NHS employee. Decide public-Pages vs
private-repo (+ paid plan) on the DATA, not the name, before first deploy. Until decided: build
with no `subject` in the JSON and do not deploy publicly.

## 2. Tailwind v4, not v3 (patches §6 and §8)
A fresh install today is Tailwind v4 (4.3.x): no tailwind.config.js, no postcss.config.js.
Use the v4 Vite-plugin flow:
  - npm install tailwindcss @tailwindcss/vite
  - add tailwindcss() to the plugins array in vite.config.ts
  - put `@import "tailwindcss";` at the top of src/style.css and import that CSS from main.ts
  - DELETE tailwind.config.js and postcss.config.js from the §8 tree — v3 only; they break v4.
(If v3's JS-config workflow is specifically wanted, pin tailwindcss@3 and say so. Default: v4.)

## 3. Field -> formatter map (clarifies §2 / lib/format.ts)
Most fields are typed `number` but mean different things. Only arithmetic is minutes/60.
  - DURATION (minutes) -> minutesToHours: all *_minutes, cross_tab values, cumulative_minutes,
    mean_minutes_per_day/week, longest_day.minutes, shortest_day.minutes.
  - CLOCK-OF-DAY (minutes from midnight) -> minuteToClock: daily start_minute/end_minute,
    flagged_segments start/end, mean_start_minute, mean_end_minute, rules.day_window_start_minute,
    rules.night_window_start_minute.  (510 -> "08:30", never "8.50 h".)
  - COUNTS (integer, raw) -> no conversion: day_count, week_count, days_touching_class
    (ByClass of DAY counts, not minutes), iso_weekday.
  - PERCENTAGES (already %) -> show with %: pct_by_band, pct_by_class.
Name-collisions to watch: start_minute/end_minute and mean_start/end_minute are clocks, not
durations; days_touching_class shares ByClass shape with minutes blocks but is counts.
Bind TS types to the REAL emitted web_data.json; it wins over the §2 sketch if they differ.

## 4. Schema gate >= 1.1.0 (tightens §10 step 3)
"schema_version starts with 1." accepts pre-audit 1.0.0, which lacks span_ok/I6 and breaks the
integrity panel. Gate on >= 1.1.0 (accept 1.x where minor >= 1), or guard each integrity field.

## 5. Automation is half-specified (patches §9 / scripts/update.sh)

**Largely answered 2026-08-18, and not the way this section assumed.** Three of
the four bullets below are settled: the headless conversion exists
(`scripts/xlsx_to_csv.py`), non-interactive git auth is moot because publishing
stays a manual act by decision, and the Pages source is set and working. The
fourth -- surfacing failures -- became `scripts/check-staleness.sh`.

There is no `update.sh` and deliberately so. A timer cannot fetch the workbook
(it is downloaded by hand) and must not publish (the push is the deploy), so the
only step left to automate was already one command. What was built instead is a
read-only daily reminder that notices the published page has gone quiet. See
`docs/TODO.md`'s Done log for the reasoning.

The original list, kept because the caveats are still true of anything that
*does* run on a schedule here:
  - xlsx -> csv must be headless/scriptable (e.g. libreoffice --headless --convert-to csv, or a
    Python xlsx reader). A manual "Save As CSV" cannot run in cron.
  - git push from cron needs non-interactive auth (gh token, SSH deploy key, or PAT) — not your
    interactive gh session.
  - update.sh must `set -euo pipefail` and surface failures (notify-send/log). The engine
    hard-errors on uncovered bank-holiday years and malformed dates; unsurfaced, the dashboard
    silently stops updating.
  - One-time: set GitHub Pages source to "GitHub Actions" in repo settings, or deploy.yml won't
    publish.

## 6. `vue-tsc --noEmit` checks NOTHING here (added 2026-07-28)
website/tsconfig.json is a references-only solution file (`"files": []`, references to
tsconfig.app.json and tsconfig.node.json). `npx vue-tsc --noEmit` therefore type-checks zero
files and always exits 0 — it is not a check, and any session claiming "vue-tsc clean" from it
has verified nothing. Use `npx vue-tsc -b` (add `--force` to bypass the incremental cache),
which is what `npm run build` runs. Confirmed 2026-07-28: with a band added to `BANDS` and no
matching label (a genuine type error), `--noEmit` exited 0 while `-b --force` failed with TS2741.

Also: run every npm/vue-tsc command from website/ with an explicit `cd` in the same command.
The shell working directory resets between tool calls in this environment.
