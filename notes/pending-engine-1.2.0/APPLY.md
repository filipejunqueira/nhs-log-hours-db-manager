# Pending: engine schema 1.2.0 — how to apply

These five files are the **finished, tested** engine side of schema 1.2.0
(hours owed + per-month breakdown). They are parked here because
`engine_v2/**` is deny-listed in `.claude/settings.json` and the lock-lift is a
deliberate act, not something a session does for itself.

Built and proven 2026-08-10 in a throwaway copy of the repo (the same method
used on 2026-07-29), so the lock only ever has to be open for a verified file
copy, never for development. Full design and success criteria: `PLAN.md` at the
repo root. Evidence for each criterion: PLAN.md's worklog section.

## The files

| file | destination | what it is |
|---|---|---|
| `afc_hours/payments.py` | `engine_v2/afc_hours/payments.py` | **new.** Payments ingest + reconciliation |
| `afc_hours/core.py` | `engine_v2/afc_hours/core.py` | months, `Totals.above_contract_min`, invariant I7 |
| `afc_hours/emit.py` | `engine_v2/afc_hours/emit.py` | schema 1.2.0, `monthly` + `payments` blocks, 3 methodology lines |
| `tests/test_payments.py` | `engine_v2/tests/test_payments.py` | **new.** 49 tests |
| `tests/test_emit.py` | `engine_v2/tests/test_emit.py` | schema tripwire re-pinned + 8 new tests |

Untouched, so not copied here: `rules.py`, `test_core.py`, `test_rules.py`,
the frozen fixture, and every data file.

## Apply it — in this order

These files are **already ruff-formatted**, so they sit cleanly on top of a
formatted base. The formatting sweep must therefore go first, as its own commit
(your decision of 2026-08-10 — see PLAN.md for why: it is 458 cosmetic lines
against 239 substantive ones on an audited file).

```
# 1. lift the lock: delete these two lines from .claude/settings.json
#      "Edit(engine_v2/**)",
#      "Write(engine_v2/**)"

# 2. commit ONE — formatting only, no behaviour change
ruff format engine_v2/afc_hours/ engine_v2/tests/
cd engine_v2 && python3 -m pytest tests/ -q && cd ..
python3 -m pytest audit/ -q
#    expect 67 + 29 green, and web_data.json unchanged
git add engine_v2 && git commit -m "style: ruff-format engine_v2 (no behaviour change)"

# 3. commit TWO — the actual change
cp notes/pending-engine-1.2.0/afc_hours/*.py engine_v2/afc_hours/
cp notes/pending-engine-1.2.0/tests/*.py     engine_v2/tests/
cd engine_v2 && python3 -m pytest tests/ -q && cd ..
python3 -m pytest audit/ -q
#    expect 116 + 29 green

# 4. restore the lock: put the two deny lines back

# 5. THEN, and only then, steps 6-7 of PLAN.md (scripts, website).
#    regen.sh cannot run against the new engine until it passes a
#    reconciliation, so do not regenerate web_data.json before step 6.
```

## What to expect afterwards

- `engine_v2/tests`: **116 passing** (was 67 — 49 new).
- `audit/`: **29 passing**, completely untouched by this work.
- `web_data.json` once regenerated: four new things and nothing removed —
  `content.monthly`, `content.payments`, `totals.above_contract_minutes`,
  `integrity.monthly_ok`. Every pre-existing key stays byte-identical
  (verified against the real log: 26 343 min, 9 weeks, to 31 Jul).
- With no `engine_v2/data/payments.csv` present, the payments block reads
  `paid 0`, `unpaid 14193`, `paid_up_to null`, empty ledger. That is correct:
  no payments have been received yet.

## Delete this folder

Once the two commits are in, this folder has served its purpose — remove it in
the same commit as step 6 so the repo does not keep a second copy of the engine
lying around.
