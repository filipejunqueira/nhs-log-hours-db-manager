# nhs-hour-log

Public dashboard rendering the locked AfC hours engine's output
(engine_v2/web_data.json, schema 1.1.0) as a legible working-hours page.
Engine = Python (built, locked). Website = Vue 3 + TS + Tailwind v4 + Vite
(not built yet), deployed to GitHub Pages.

## Read first
- docs/WEBSITE_PLAN.md — authoritative plan: data contract, types, repo
  structure, build order (§10).
- docs/BUILD_NOTES.md — corrections to the plan; THESE WIN where they conflict.
  Read before scaffolding: Tailwind v4 (not the v3 layout in §6/§8), the
  field→formatter map, schema gate ≥1.1.0, automation gaps, the privacy decision.

## Cardinal rules
- Do NOT modify engine_v2/ — complete, audited, locked (also denied in
  .claude/settings.json). Treat its JSON output as a fixed contract.
- The engine determines every hours figure; the front end only re-presents
  them and shows no money. Permitted browser arithmetic, confined to
  website/src/lib/format.ts: minutes ÷ 60 for display, HH:MM clock formatting,
  and sums of already-computed minute values (sumMinutes). The browser never
  classifies, bands, or produces a figure the engine could disagree with.
  (Amended 2026-07-19, user decision; derived figures move into the engine
  output at the next schema bump.)
- Identity-light: no `subject` in the committed JSON until the §7 visibility
  decision is made.
