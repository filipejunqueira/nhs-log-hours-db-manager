"""
test_emit.py -- exercises afc_hours/emit.py

Run standalone:  python3 tests/test_emit.py
Or with pytest:  pytest tests/test_emit.py
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from afc_hours import core, emit, rules  # noqa: E402

REAL_LOG = os.environ.get("AFC_REAL_LOG") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "filipe_working_hours_log_25-06-2026.csv")
PINNED = datetime(2026, 6, 26, 0, 0, 0, tzinfo=timezone.utc)


def _payload(generated_at=PINNED, subject=None):
    res = core.compute_from_csv(REAL_LOG)
    return emit.build_payload(res, generated_at=generated_at, subject=subject)


# --- shape ---
def test_top_level_is_meta_and_content():
    p = _payload()
    assert set(p.keys()) == {"meta", "content"}


def test_meta_envelope_fields():
    m = _payload()["meta"]
    assert m["schema_version"] == emit.SCHEMA_VERSION
    assert m["unit"] == "minutes"
    assert m["generated_at"] == "2026-06-26T00:00:00Z"
    assert m["contract"]["contracted_weekly_minutes"] == 1350
    assert m["contract"]["fulltime_weekly_minutes"] == 2250
    assert m["contract"]["pay_week_start"] == "monday"


def test_meta_rules_match_the_law():
    m = _payload()["meta"]
    assert m["rules"]["day_window_start_minute"] == 360
    assert m["rules"]["night_window_start_minute"] == 1200
    assert m["rules"]["bank_holidays"] == [d.isoformat() for d in sorted(rules.BANK_HOLIDAYS)]
    assert m["rules"]["bank_holiday_years_covered"] == [2026, 2027]


def test_methodology_present_and_mentions_minutes():
    meth = _payload()["meta"]["methodology"]
    assert any("minutes" in line.lower() for line in meth)
    assert any("22.5" in line for line in meth)


def test_content_totals_match_core():
    res = core.compute_from_csv(REAL_LOG)
    c = emit.build_payload(res, generated_at=PINNED)["content"]
    assert c["totals"]["total_minutes"] == res.totals.total_min == 11919
    assert c["totals"]["minutes_by_band"] == {"contracted": 5400, "additional": 3600, "overtime": 2919}
    assert c["totals"]["minutes_by_class"]["sunday"] == 953
    assert c["totals"]["unsocial_within_baseline_minutes"] == 0


def test_enum_dicts_use_string_keys():
    c = _payload()["content"]
    assert set(c["totals"]["minutes_by_band"]) == {"contracted", "additional", "overtime"}
    assert "sunday" in c["totals"]["minutes_by_class"]
    assert set(c["cross_tab"]) == {"contracted", "additional", "overtime"}


def test_integrity_block_all_true():
    ig = _payload()["content"]["integrity"]
    assert ig["conservation_ok"] and ig["partitions_ok"] and ig["uniqueness_ok"]
    assert ig["banding_formula_ok"] and ig["crosstab_ok"] and ig["span_ok"]
    assert ig["total_raw_minutes"] == ig["total_segment_minutes"] == 11919


def test_schema_version_is_current():
    assert emit.SCHEMA_VERSION == "1.1.0"
    assert _payload()["meta"]["schema_version"] == "1.1.0"


def test_methodology_documents_mean_denominator():
    meth = _payload()["meta"]["methodology"]
    assert any("averaged over" in line and "recorded" in line for line in meth)


def test_weekly_and_daily_present():
    c = _payload()["content"]
    assert {w["iso_week"] for w in c["weekly"]} == {"2026-W23", "2026-W24", "2026-W25", "2026-W26"}
    assert len(c["daily"]) == 21
    assert len(c["cumulative"]) == 21
    assert c["cumulative"][-1]["cumulative_minutes"] == 11919


# --- determinism ---
def test_identical_inputs_give_identical_bytes():
    res = core.compute_from_csv(REAL_LOG)
    a = emit.to_json(res, generated_at=PINNED)
    b = emit.to_json(res, generated_at=PINNED)
    assert a == b


def test_only_timestamp_varies_with_time():
    res = core.compute_from_csv(REAL_LOG)
    t1 = datetime(2026, 6, 26, 0, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 7, 1, 23, 30, 0, tzinfo=timezone.utc)
    p1 = emit.build_payload(res, generated_at=t1)
    p2 = emit.build_payload(res, generated_at=t2)
    assert p1["meta"]["generated_at"] != p2["meta"]["generated_at"]
    assert p1["content"] == p2["content"]            # content is time-invariant
    m1 = dict(p1["meta"]); m2 = dict(p2["meta"])
    m1.pop("generated_at"); m2.pop("generated_at")
    assert m1 == m2                                   # rest of meta identical too


def test_output_is_valid_json():
    json.loads(emit.to_json(core.compute_from_csv(REAL_LOG), generated_at=PINNED))


# --- money-free guards ---
_MONEY_KEY_TOKENS = {"salary", "gbp", "wage", "rate", "rates", "multiplier",
                     "pension", "premium", "cost", "money", "gross", "net"}


def _all_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_keys(v)


def test_no_money_keys_anywhere():
    p = _payload()
    for k in _all_keys(p):
        tokens = set(k.lower().split("_"))          # whole-token match, not substring
        bad = _MONEY_KEY_TOKENS & tokens
        assert not bad, f"money-like key {k!r} (token {bad})"


def test_no_currency_symbol_in_output():
    s = emit.to_json(core.compute_from_csv(REAL_LOG), generated_at=PINNED)
    assert "£" not in s and "gbp" not in s.lower()


def test_emit_module_does_not_import_money():
    # The structural guarantee is the import graph: emit must never import money.
    # (The word "money" legitimately appears in emit.py's docstring describing this.)
    src = open(os.path.join(os.path.dirname(__file__), "..", "afc_hours", "emit.py"),
               encoding="utf-8").read()
    for line in src.splitlines():
        s = line.strip()
        if (s.startswith("import ") or s.startswith("from ")) and "money" in s:
            raise AssertionError(f"emit.py imports money: {s!r}")


def test_subject_omitted_by_default_included_when_given():
    assert "subject" not in _payload()["meta"]
    p = _payload(subject={"name": "Test"})
    assert p["meta"]["subject"] == {"name": "Test"}


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in funcs:
        try:
            fn()
        except AssertionError as e:
            print(f"FAIL  {fn.__name__}\n      {e}")
        except Exception as e:  # noqa: BLE001
            print(f"ERROR {fn.__name__}\n      {type(e).__name__}: {e}")
        else:
            passed += 1
            print(f"pass  {fn.__name__}")
    print(f"\n{passed}/{len(funcs)} checks passed")
    sys.exit(0 if passed == len(funcs) else 1)
