"""
rules.py -- THE LAW (constants only)
====================================

Single home for every invariant magnitude and date the *hours* engine obeys.

Contract for this module:
  * Constants ONLY. No functions, no classes, no I/O, no logic, no flags.
  * No money. Rates, multipliers, salary and pension tiers live in `money.py`,
    because money has variants and this file must stay invariant. As a result,
    nothing `core.py` can import from here can possibly express a pay rate, which
    is what makes "the hours path cannot touch money" true by construction.
  * Changing any value here is a deliberate, reviewed, version-bumped edit to the
    rules -- never a runtime toggle.

What deliberately lives ELSEWHERE (so an auditor knows where to look):
  * Unsocial rates (+30% / +60%), overtime multipliers (x1.5 / x2.0), salary,
    pension tiers ....................................  money.py   (Part ii)
  * Category enums (ThresholdBand / UnsocialClass / DayType) and all banding /
    classification LOGIC ............................   core.py    (Part i)
  * JSON shape identifier (schema_version) .........   emit.py

Sources are cited inline: "AfC" = NHS Terms & Conditions Handbook (Amendment 62,
1 June 2026); bank holidays = gov.uk, England & Wales.
"""

from datetime import date, time
from typing import Final

# ---------------------------------------------------------------------------
# Weekly thresholds  (AfC Section 3 -- part-time additional-hours rule)
# ---------------------------------------------------------------------------
# Hours 0 -> 22.5      : contracted baseline (within salary)
# Hours 22.5 -> 37.5   : additional standard hours (plain time + any unsocial)
# Hours above 37.5     : overtime
CONTRACTED_WEEKLY_HOURS: Final[float] = 22.5   # 0.6 FTE contract
FULLTIME_WEEKLY_HOURS: Final[float] = 37.5     # AfC whole-time equivalent

# ---------------------------------------------------------------------------
# Pay-week boundary
# ---------------------------------------------------------------------------
# Banding accumulates hours within one pay-week, in chronological order, against
# the thresholds above. The week starts on Monday.
#
# Value uses date.weekday() convention: Monday=0 .. Sunday=6.
#
# NOTE: the boundary is ASSUMED Monday and is UNCONFIRMED against LTHT's ESR
# definition. Because the boundary changes which hours cross 37.5h, it is an
# HOURS decision, not a money decision, so it is fixed here as law. If LTHT
# confirms a different boundary, that is a reviewed one-line edit here plus a
# schema_version bump -- never a runtime flag.
PAY_WEEK_START_WEEKDAY: Final[int] = 0   # Monday

# ---------------------------------------------------------------------------
# Clock boundaries for unsocial classification  (AfC Section 2)
# ---------------------------------------------------------------------------
# Weekday unsocial window is 20:00 up to 06:00 (i.e. evenings/nights). Daytime
# is 06:00 up to 20:00. These are the raw boundary times; the precise
# inclusive/exclusive handling and the splitting of a shift that crosses a
# boundary are enforced in core.py (clock-time split, not the para-2.11
# half-shift rule -- a deliberate, documented choice made in core).
DAY_START: Final[time] = time(6, 0)     # 06:00 -- start of daytime
NIGHT_START: Final[time] = time(20, 0)  # 20:00 -- start of weekday unsocial window

# Saturday, Sunday and bank holidays are unsocial for the WHOLE day, midnight to
# midnight, with no intra-day 06:00/20:00 split and a single class per day
# (AfC Section 2, para 2.10). core.py reads this as the governing rule.
WEEKEND_AND_BANKHOL_WHOLE_DAY: Final[bool] = True

# ---------------------------------------------------------------------------
# Bank holidays -- England & Wales (gov.uk)
# ---------------------------------------------------------------------------
# Substitute days are already resolved to the actual observed date (e.g. when
# 26 Dec falls on a weekend the holiday moves to the next weekday). Every entry
# below has been verified to fall on the expected weekday.
#
# MAINTENANCE: this table covers the years in BANK_HOLIDAY_YEARS_COVERED only.
# core.py refuses to classify any date whose year is outside that set, so an
# out-of-range date fails loudly rather than being silently mis-rated. Extend
# both this set and the years-covered set together, from gov.uk, when needed.
BANK_HOLIDAYS: Final[frozenset[date]] = frozenset({
    # --- 2026 ---
    date(2026, 1, 1),    # New Year's Day            (Thu)
    date(2026, 4, 3),    # Good Friday               (Fri)
    date(2026, 4, 6),    # Easter Monday             (Mon)
    date(2026, 5, 4),    # Early May bank holiday    (Mon)
    date(2026, 5, 25),   # Spring bank holiday       (Mon)
    date(2026, 8, 31),   # Summer bank holiday       (Mon)
    date(2026, 12, 25),  # Christmas Day             (Fri)
    date(2026, 12, 28),  # Boxing Day (substitute)   (Mon; 26 Dec is a Sat)
    # --- 2027 ---
    date(2027, 1, 1),    # New Year's Day            (Fri)
    date(2027, 3, 26),   # Good Friday               (Fri)
    date(2027, 3, 29),   # Easter Monday             (Mon)
    date(2027, 5, 3),    # Early May bank holiday    (Mon)
    date(2027, 5, 31),   # Spring bank holiday       (Mon)
    date(2027, 8, 30),   # Summer bank holiday       (Mon)
    date(2027, 12, 27),  # Christmas Day (substitute) (Mon; 25 Dec is a Sat)
    date(2027, 12, 28),  # Boxing Day (substitute)   (Tue; 26 Dec is a Sun)
})

# Years for which BANK_HOLIDAYS is known to be complete. Drives core's guard.
BANK_HOLIDAY_YEARS_COVERED: Final[frozenset[int]] = frozenset({2026, 2027})
