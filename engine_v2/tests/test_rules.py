"""
test_rules.py -- locks the constants in afc_hours/rules.py

Three kinds of check:
  1. External truth   -- bank-holiday dates match the gov.uk England & Wales
                         list (independently restated here) and each lands on
                         its expected weekday (proves substitute days resolved).
  2. Internal sanity  -- threshold/boundary ordering, years-covered matches the
                         table, no holiday on a weekend.
  3. Money-free guard -- the module exposes constants only (no callables defined
                         here) and no symbol name hints at money.

Run standalone:  python3 tests/test_rules.py
Or with pytest:  pytest tests/test_rules.py
"""

import os
import sys
from datetime import date, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from afc_hours import rules  # noqa: E402


# --- 1. External truth: the gov.uk England & Wales list, restated independently ---
EXPECTED_BANK_HOLIDAYS = {
    date(2026, 1, 1):  "Thursday",   # New Year's Day
    date(2026, 4, 3):  "Friday",     # Good Friday
    date(2026, 4, 6):  "Monday",     # Easter Monday
    date(2026, 5, 4):  "Monday",     # Early May
    date(2026, 5, 25): "Monday",     # Spring
    date(2026, 8, 31): "Monday",     # Summer
    date(2026, 12, 25): "Friday",    # Christmas Day
    date(2026, 12, 28): "Monday",    # Boxing Day (substitute)
    date(2027, 1, 1):  "Friday",     # New Year's Day
    date(2027, 3, 26): "Friday",     # Good Friday
    date(2027, 3, 29): "Monday",     # Easter Monday
    date(2027, 5, 3):  "Monday",     # Early May
    date(2027, 5, 31): "Monday",     # Spring
    date(2027, 8, 30): "Monday",     # Summer
    date(2027, 12, 27): "Monday",    # Christmas Day (substitute)
    date(2027, 12, 28): "Tuesday",   # Boxing Day (substitute)
}


def test_bank_holidays_exactly_match_expected_set():
    assert rules.BANK_HOLIDAYS == frozenset(EXPECTED_BANK_HOLIDAYS), (
        "rules.BANK_HOLIDAYS diverges from the gov.uk list restated in this test"
    )


def test_each_bank_holiday_falls_on_expected_weekday():
    for d, expected_dow in EXPECTED_BANK_HOLIDAYS.items():
        assert d.strftime("%A") == expected_dow, (
            f"{d.isoformat()} is a {d.strftime('%A')}, expected {expected_dow}"
        )


def test_no_bank_holiday_falls_on_a_weekend():
    # All observed holidays (after substitution) must be weekdays Mon-Fri.
    for d in rules.BANK_HOLIDAYS:
        assert d.weekday() < 5, f"{d.isoformat()} falls on a weekend; substitute not resolved"


def test_eight_holidays_per_covered_year():
    for yr in rules.BANK_HOLIDAY_YEARS_COVERED:
        n = sum(1 for d in rules.BANK_HOLIDAYS if d.year == yr)
        assert n == 8, f"{yr} has {n} bank holidays, expected 8"


# --- 2. Internal consistency ---
def test_threshold_ordering_and_values():
    assert rules.CONTRACTED_WEEKLY_HOURS == 22.5
    assert rules.FULLTIME_WEEKLY_HOURS == 37.5
    assert rules.CONTRACTED_WEEKLY_HOURS < rules.FULLTIME_WEEKLY_HOURS


def test_pay_week_starts_monday():
    assert rules.PAY_WEEK_START_WEEKDAY == 0  # Monday, date.weekday() convention


def test_clock_boundaries():
    assert rules.DAY_START == time(6, 0)
    assert rules.NIGHT_START == time(20, 0)
    assert rules.DAY_START < rules.NIGHT_START
    assert rules.WEEKEND_AND_BANKHOL_WHOLE_DAY is True


def test_years_covered_matches_table():
    years_in_table = {d.year for d in rules.BANK_HOLIDAYS}
    assert years_in_table == set(rules.BANK_HOLIDAY_YEARS_COVERED), (
        "BANK_HOLIDAY_YEARS_COVERED must equal the years actually present in the table"
    )


# --- 3. Money-free / constants-only guard ---
_IMPORTED_NAMES = {"date", "time", "Final"}  # imports, legitimately callable
_MONEY_HINTS = (
    "rate", "salary", "pay", "wage", "gbp", "pound", "money", "cost",
    "enhanc", "premium", "tier", "pension", "multiplier",
)
# Tokens that legitimately contain a money-hint substring but are NOT money:
# "pay week" is the payroll term for the time boundary (an hours concept).
_ALLOWED_TOKENS = ("pay_week",)


def _scrub(name_low):
    for tok in _ALLOWED_TOKENS:
        name_low = name_low.replace(tok, "")
    return name_low


def _public_constants():
    for name in dir(rules):
        if name.startswith("_") or name in _IMPORTED_NAMES:
            continue
        yield name, getattr(rules, name)


def test_module_defines_constants_only_no_callables():
    for name, val in _public_constants():
        assert not callable(val), (
            f"rules.{name} is callable; rules.py must contain constants only"
        )


def test_no_symbol_name_hints_at_money():
    for name, _ in _public_constants():
        low = _scrub(name.lower())
        for hint in _MONEY_HINTS:
            assert hint not in low, (
                f"rules.{name} looks money/rate-related ('{hint}'); money belongs in money.py"
            )


def test_constant_value_types_are_expected():
    # Every public constant is one of: number, time, bool, or frozenset (of date/int).
    for name, val in _public_constants():
        assert isinstance(val, (int, float, bool, time, frozenset)), (
            f"rules.{name} has unexpected type {type(val).__name__}"
        )


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in funcs:
        try:
            fn()
        except AssertionError as e:
            print(f"FAIL  {fn.__name__}\n      {e}")
        else:
            passed += 1
            print(f"pass  {fn.__name__}")
    print(f"\n{passed}/{len(funcs)} checks passed")
    sys.exit(0 if passed == len(funcs) else 1)
