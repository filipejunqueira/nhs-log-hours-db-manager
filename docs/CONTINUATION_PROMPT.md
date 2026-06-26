<continuation_prompt>
  <origin>
    <session_date>2026-06-26</session_date>
    <summary>
      Built and audited Part (i) of the AfC hours engine (v2) — a deterministic,
      minutes-only, money-free Python package that turns a CSV of working
      start/end times into a website JSON. Produced rules.py, core.py, emit.py
      with paired tests (67 checks, all passing). Ran an external multi-LLM audit,
      then implemented its findings (overlap/duplicate rejection + a new per-day
      span invariant I6, plus diagnostic and documentation fixes), bumping the
      output schema to 1.1.0. The engine is now considered complete and locked.
      This session ends by pivoting to the public dashboard, which the user will
      build with Claude Code; it produced WEBSITE_PLAN.md (functionality + repo
      structure + data contract) and this handoff.
    </summary>
    <chat_url>(web chat; not Claude Code)</chat_url>
  </origin>

  <instructions>
    The receiving session is Claude Code working inside the repo at
    ~/code/nhs-hour-log. Steps:
    1. Read docs/WEBSITE_PLAN.md in full — it is the authoritative plan for the
       website, the data contract, the TypeScript types, the repo structure, the
       deployment flow, and the build order.
    2. Read engine_v2/web_data.json — this is the EXACT data shape the site
       consumes (schema 1.1.0). Bind TypeScript types to it (types are sketched in
       the plan, §2).
    3. Optionally skim engine_v2/AUDIT_BRIEF.md for how the numbers are computed
       (helps write the methodology/integrity panels accurately).
    4. Build the website per WEBSITE_PLAN.md §10 (build order). Scaffold website/
       with Vite (vue-ts) + Tailwind; build the v1 components first.
    DO NOT modify anything in engine_v2/ — the Python engine is complete and
    independently audited. Treat its JSON output as a fixed contract. DO NOT
    re-derive the hours logic or reimplement any calculation in the front end; the
    site only renders pre-computed JSON (the sole permitted browser arithmetic is
    minutes ÷ 60 for display).
  </instructions>

  <decisions_made>
    <!-- Engine (locked; do not revisit) -->
    <d>Hours are split into Part (i) = deterministic hours engine producing the
       JSON (no flags, no money), and Part (ii) = money.py (rates + variants),
       NOT YET BUILT. The dependency graph enforces money can never reach the JSON
       (emit.py does not import money).</d>
    <d>Everything computes in INTEGER MINUTES; no floats, no rounding in the hours
       path. Hours are a display convenience only (mins ÷ 60). Thresholds: 1350
       min (22.5h) contracted, 2250 min (37.5h) full-time/overtime line.</d>
    <d>Pay-week is Monday–Sunday, fixed as law in rules.py (NOT a runtime flag),
       because the boundary changes banding. It is UNCONFIRMED vs LTHT's actual
       ESR pay-week; changing it later is a reviewed edit + schema bump.</d>
    <d>Banding is chronological within the week (first 1350 min = contracted, etc.).
       The "22.5h-before-any-extra" rule is enforced as runtime invariant I4.
       Unsocial hours that fall inside the baseline are CLASSIFIED strictly but
       FLAGGED (unsocial_within_baseline) rather than suppressed — the money layer
       decides whether to claim them. On the real log this flag is 0.</d>
    <d>External audit (3 LLMs) found the core maths correct. Implemented its
       findings: overlap/duplicate same-date rows now hard-error (were summed);
       added invariant I6 (per-day worked minutes ≤ clock span, reported as
       span_ok); split the End≤Start message (zero-length vs End-before-Start);
       dotted dates reported as unrecognised format not ambiguous; non-zero
       seconds rejected not truncated; mean denominator documented. Output schema
       bumped 1.0.0 → 1.1.0. No figure changed for well-formed input.</d>

    <!-- Dashboard (settled this session) -->
    <d>Front end does ZERO calculation; renders pre-computed JSON only. Minutes →
       hours conversion is the only browser arithmetic.</d>
    <d>Stack: Vue 3 + TypeScript + Tailwind + Vite, on GitHub Pages. Site fetches
       web_data.json at runtime from BASE_URL; validates schema_version.</d>
    <d>Site must make the hour computation legible (render meta.methodology
       verbatim; show the integrity checks as computed green ticks) so a payroll
       reader can apply enhancements themselves, WITHOUT the page asserting any
       rate or leading the reader.</d>
    <d>Design register: calm, professional, NHS-adjacent (matching the earlier
       hours report), accessible, no trackers.</d>
    <d>v1 scope = summary, totals, weekly table, daily log, methodology panel,
       integrity panel. v1.1 = cross-tab, cumulative chart, distribution stats
       (data already in the JSON; additive).</d>
    <d>Deployment: single branch (main). GitHub Action builds website/ and deploys
       on push. Daily update is a cron running scripts/update.sh
       (export xlsx→csv → run engine → copy web_data.json into website/public →
       commit/push); a daily rebuild of the tiny app is acceptable.</d>

    <!-- Explicitly parked -->
    <d>money.py (Part ii) deferred until after the dashboard. Overnight-shift
       support deferred a few months (currently a hard error by design).</d>
  </decisions_made>

  <next_steps>
    1. [USER DECISION, before first public deploy] Identity & hosting (WEBSITE_PLAN
       §7): public vs private repo; whether to include the worker's name. Build
       identity-light (no `subject` in JSON) until decided.
    2. Scaffold website/ (Vite vue-ts + Tailwind); set `base` in vite.config.ts to
       the Pages sub-path.
    3. Add src/types/web-data.ts and src/lib/format.ts (the only converters).
    4. Add useHoursData composable (fetch + schema check).
    5. Build v1 components (summary, totals, weekly, daily, methodology, integrity).
    6. Drop a real web_data.json into website/public for dev; verify against the
       known figures (11919 min total; bands 5400/3600/2919; all integrity flags
       true; within-baseline 0).
    7. Add .github/workflows/deploy.yml and scripts/update.sh.
    8. v1.1: cross-tab, cumulative chart, stats.
    9. (Later, separate effort) Build money.py = Part (ii), then a private financial
       view; the D2 overtime×unsocial variants (strict-floor 1.5 / higher-of 1.6 /
       stacking 2.1) live there as flags, never in the hours path.
  </next_steps>

  <files_to_upload>
    The repo already contains the engine; these are the files the next session
    needs in place (paths relative to repo root ~/code/nhs-hour-log):
    - engine_v2/afc_hours/{rules.py, core.py, emit.py, __init__.py}  (built; do not modify)
    - engine_v2/tests/{test_rules.py, test_core.py, test_emit.py}     (67 checks, all pass)
    - engine_v2/data/filipe_working_hours_log_25-06-2026.csv          (sample input)
    - engine_v2/web_data.json                                         (THE DATA CONTRACT, schema 1.1.0)
    - engine_v2/AUDIT_BRIEF.md                                        (how the numbers are computed)
    ADD these two documents to the repo (recommended location docs/):
    - docs/WEBSITE_PLAN.md        (the website plan — read first)
    - docs/CONTINUATION_PROMPT.md (this file)
  </files_to_upload>

  <domain_state>
    <engine>
      Status: COMPLETE, audited, locked. Schema 1.1.0. Pure-stdlib, Python 3.10+.
      Modules: rules.py (constants/law), core.py (ingest+classify+band+stats+
      invariants), emit.py (JSON). money.py NOT built.
      Tests: rules 11, core 39, emit 17 = 67, all passing.
      Six runtime invariants I1–I6 (conservation, partition exhaustion, uniqueness,
      banding-formula, cross-tab, per-day span). Money-free guaranteed structurally
      (emit does not import money).
      Real-log figures (filipe_working_hours_log_25-06-2026.csv, 21 days, ISO
      W23–W26): total 11919 min (≈198.65 h); bands contracted 5400 / additional
      3600 / overtime 2919; classes daytime 10815 / weekday_night 151 / saturday 0
      / sunday 953 / bank_holiday 0; unsocial_within_baseline 0; all integrity OK.
    </engine>
    <website>
      Status: NOT STARTED. Plan written (docs/WEBSITE_PLAN.md). Stack chosen
      (Vue3+TS+Tailwind+Vite, GitHub Pages). v1 scope defined. Identity/hosting
      undecided.
    </website>
    <repo>
      Current: ~/code/nhs-hour-log/ contains only engine_v2/. Target structure in
      WEBSITE_PLAN.md §8 (engine_v2/, website/, scripts/, .github/workflows/,
      docs/). The website's data input is engine_v2/web_data.json, copied to
      website/public/web_data.json by scripts/update.sh.
    </repo>
    <open_user_decisions>
      - Identity (show name? inject at deploy?) and hosting (public vs private/paid)
        — required before first public deploy.
      - Final v1 vs v1.1 scope at build time (recommendation: ship v1 first).
    </open_user_decisions>
  </domain_state>
</continuation_prompt>
