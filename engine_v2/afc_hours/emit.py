"""
emit.py -- serialise a HoursResult to the website JSON
======================================================

Contract:
  * MINUTES ONLY. No hours appear in the file; the front end divides by 60 for
    display. This sidesteps all rounding: the stored figures are exact integers.
  * MONEY-FREE BY CONSTRUCTION. This module imports `core` and `rules` and never
    imports `money`. The token "money" does not appear here (a test enforces it),
    so the JSON path cannot carry a pay figure.
  * DETERMINISTIC CONTENT. Same HoursResult -> identical `content` bytes. Dicts
    are built in a fixed order (readable, not sort_keys); the only field that
    varies between runs is meta.generated_at, which is injectable so tests can
    pin it and so the *content* stays a pure function of the result.

Layout of the emitted object:
    { "meta": {...envelope, the law, methodology...},
      "content": {...period, totals, weekly, daily, cross_tab,
                  cumulative, statistics, integrity...} }
"""

import json
from datetime import datetime, timezone

from afc_hours import core, rules
from afc_hours.core import ThresholdBand, UnsocialClass

SCHEMA_VERSION = "1.1.0"

METHODOLOGY = [
    "All durations are in minutes. Divide by 60 for hours.",
    "A pay-week runs Monday to Sunday.",
    "Within each week the first 1350 minutes (22.5 hours) worked are contracted; "
    "minutes 1350 to 2250 are additional standard hours; minutes above 2250 "
    "(37.5 hours) are overtime. Minutes are attributed in the order they were worked.",
    "Unsocial classes are by clock time: weekday work between 20:00 and 06:00 is "
    "'weekday night'; Saturday, Sunday and bank holidays are unsocial for the whole day.",
    "'unsocial_within_baseline_minutes' counts any unsocial minutes that fell within "
    "the first 22.5 hours of a week. It is listed for transparency; normally it is zero.",
    "Mean figures (per day, per week) are averaged over the days and weeks in which work "
    "was recorded, not over every calendar day or week in the period.",
    "This file contains hours only. Pay rates are determined separately.",
]


# --- helpers: enum-keyed dict -> string-keyed dict in fixed enum order ---
def _by_band(d: dict) -> dict:
    return {b.value: d[b] for b in ThresholdBand}


def _by_class(d: dict) -> dict:
    return {c.value: d[c] for c in UnsocialClass}


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# --- meta envelope (the law + methodology; no computed content) ---
def _meta(generated_at: datetime, subject: dict | None) -> dict:
    meta = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _iso(generated_at),
        "unit": "minutes",
        "unit_note": "All durations are in minutes; divide by 60 for hours.",
        "contract": {
            "contracted_weekly_minutes": core.CONTRACTED_MIN,
            "fulltime_weekly_minutes": core.FULLTIME_MIN,
            "pay_week_start": "monday",
        },
        "rules": {
            "day_window_start_minute": core.DAY_START_MIN,
            "night_window_start_minute": core.NIGHT_START_MIN,
            "weekend_and_bankhol_whole_day": rules.WEEKEND_AND_BANKHOL_WHOLE_DAY,
            "bank_holidays": [d.isoformat() for d in sorted(rules.BANK_HOLIDAYS)],
            "bank_holiday_years_covered": sorted(rules.BANK_HOLIDAY_YEARS_COVERED),
        },
        "methodology": list(METHODOLOGY),
    }
    if subject:
        meta["subject"] = dict(subject)
    return meta


# --- content block (the computed result; deterministic given the result) ---
def _weekly(weeks) -> list:
    out = []
    for w in weeks:
        out.append({
            "iso_week": w.iso_week,
            "monday": w.monday.isoformat(),
            "day_count": w.day_count,
            "total_minutes": w.total_min,
            "minutes_by_band": _by_band(w.minutes_by_band),
            "minutes_by_class": _by_class(w.minutes_by_class),
            "unsocial_within_baseline_minutes": w.unsocial_within_baseline_min,
            "flagged_segments": [
                {
                    "date": f.date.isoformat(),
                    "start_minute": f.start_min,
                    "end_minute": f.end_min,
                    "duration_minutes": f.duration_min,
                    "unsocial_class": f.unsocial_class.value,
                }
                for f in w.flagged_segments
            ],
        })
    return out


def _daily(days) -> list:
    return [
        {
            "date": r.date.isoformat(),
            "iso_weekday": r.iso_weekday,
            "day_type": r.day_type.value,
            "start_minute": r.start_min,
            "end_minute": r.end_min,
            "duration_minutes": r.duration_min,
            "minutes_by_class": _by_class(r.minutes_by_class),
        }
        for r in days
    ]


def _statistics(s) -> dict:
    return {
        "pct_by_band": _by_band(s.pct_by_band),
        "pct_by_class": _by_class(s.pct_by_class),
        "mean_minutes_per_day": s.mean_min_per_day,
        "mean_minutes_per_week": s.mean_min_per_week,
        "mean_start_minute": s.mean_start_min,
        "mean_end_minute": s.mean_end_min,
        "longest_day": {"date": s.longest_day[0].isoformat(), "minutes": s.longest_day[1]},
        "shortest_day": {"date": s.shortest_day[0].isoformat(), "minutes": s.shortest_day[1]},
        "days_touching_class": _by_class(s.days_touching_class),
    }


def _integrity(ig) -> dict:
    return {
        "conservation_ok": ig.conservation_ok,
        "partitions_ok": ig.partitions_ok,
        "uniqueness_ok": ig.uniqueness_ok,
        "banding_formula_ok": ig.banding_formula_ok,
        "crosstab_ok": ig.crosstab_ok,
        "span_ok": ig.span_ok,
        "total_raw_minutes": ig.total_raw_min,
        "total_segment_minutes": ig.total_segment_min,
        "unsocial_within_baseline_minutes": ig.unsocial_within_baseline_min,
        "warnings": list(ig.warnings),
    }


def _content(result: core.HoursResult) -> dict:
    t = result.totals
    return {
        "period": {"start": result.period.start.isoformat(),
                   "end": result.period.end.isoformat()},
        "totals": {
            "total_minutes": t.total_min,
            "day_count": t.day_count,
            "week_count": t.week_count,
            "minutes_by_band": _by_band(t.minutes_by_band),
            "minutes_by_class": _by_class(t.minutes_by_class),
            "unsocial_within_baseline_minutes": t.unsocial_within_baseline_min,
        },
        "weekly": _weekly(result.weeks),
        "daily": _daily(result.days),
        "cross_tab": {b.value: _by_class(result.cross_tab[b]) for b in ThresholdBand},
        "cumulative": [{"date": p.date.isoformat(), "cumulative_minutes": p.cumulative_min}
                       for p in result.cumulative],
        "statistics": _statistics(result.statistics),
        "integrity": _integrity(result.integrity),
    }


# --- public API ---
def build_payload(result: core.HoursResult, *, generated_at: datetime | None = None,
                  subject: dict | None = None) -> dict:
    """HoursResult -> JSON-ready dict. `content` is pure in `result`; only
    `meta.generated_at` varies with time (injectable for deterministic tests)."""
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)
    return {"meta": _meta(generated_at, subject), "content": _content(result)}


def to_json(result: core.HoursResult, *, generated_at: datetime | None = None,
            subject: dict | None = None) -> str:
    payload = build_payload(result, generated_at=generated_at, subject=subject)
    # fixed-order dicts already; ensure_ascii=False keeps real characters; trailing newline.
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def write_json(result: core.HoursResult, path: str, *, generated_at: datetime | None = None,
               subject: dict | None = None) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_json(result, generated_at=generated_at, subject=subject))
