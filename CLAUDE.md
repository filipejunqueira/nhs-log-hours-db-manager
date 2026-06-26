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
- Front end does zero calculation and shows no money. The only browser
  arithmetic is minutes ÷ 60 for display.
- Identity-light: no `subject` in the committed JSON until the §7 visibility
  decision is made.
