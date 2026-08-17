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
from afc_hours import payments as payments_mod
from afc_hours.core import ThresholdBand, UnsocialClass

SCHEMA_VERSION = "1.2.0"

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
    "Monthly figures group each minute by the calendar month it was worked in. "
    "Threshold bands are always decided by the Monday-to-Sunday pay-week, so a week "
    "spanning a month boundary contributes minutes to both months carrying the bands "
    "its week assigned; months are never re-banded against a monthly baseline.",
    "'above_contract_minutes' is everything beyond the contracted 22.5 hours a week, "
    "that is additional plus overtime. It does NOT include "
    "'unsocial_within_baseline_minutes': those minutes fall inside the contracted "
    "22.5 hours and so are not above contract, however they are enhanced.",
    "Payments record how many minutes of above-contract work have been settled, never "
    "at what price. Each payment settles the oldest unsettled pay-week first; the total "
    "still owed does not depend on that ordering.",
    "This file contains hours only. Pay rates are determined separately.",
]


# --- helpers: enum-keyed dict -> string-keyed dict in fixed enum order ---
def _by_band(d: dict) -> dict:
    return {b.value: d[b] for b in ThresholdBand}


def _by_class(d: dict) -> dict:
    return {c.value: d[c] for c in UnsocialClass}


def _iso(dt: datetime) -> str:
    return (
        dt.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


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
        out.append(
            {
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
            }
        )
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


def _monthly(months) -> list:
    return [
        {
            "month": m.month,
            "day_count": m.day_count,
            "total_minutes": m.total_min,
            "minutes_by_band": _by_band(m.minutes_by_band),
            "minutes_by_class": _by_class(m.minutes_by_class),
        }
        for m in months
    ]


def _payments(rec) -> dict:
    """Serialise a Reconciliation. Note there is NO note field: LedgerEntry has
    none, so payment free-text cannot reach this file even by accident."""
    return {
        "paid_minutes": rec.paid_min,
        "unpaid_minutes": rec.unpaid_min,
        "overpaid_minutes": rec.overpaid_min,
        "paid_up_to": rec.paid_up_to.isoformat() if rec.paid_up_to else None,
        "ledger": [
            {
                "date": e.date.isoformat(),
                "minutes_paid": e.minutes_paid,
                "cumulative_paid_minutes": e.cumulative_paid_min,
            }
            for e in rec.ledger
        ],
        "unpaid_weeks": [
            {
                "iso_week": s.iso_week,
                "monday": s.monday.isoformat(),
                "extra_minutes": s.extra_min,
                "unpaid_minutes": s.unpaid_min,
            }
            for s in rec.unpaid_weeks
        ],
        # Payment warnings live HERE and never in content.integrity.warnings.
        # regen.sh, ingest-check.sh and deploy.sh all refuse to publish while
        # integrity.warnings is non-empty; routing an overpayment in there
        # would make the first real overpayment permanently unpublishable.
        "warnings": list(rec.warnings),
    }


def _statistics(s) -> dict:
    return {
        "pct_by_band": _by_band(s.pct_by_band),
        "pct_by_class": _by_class(s.pct_by_class),
        "mean_minutes_per_day": s.mean_min_per_day,
        "mean_minutes_per_week": s.mean_min_per_week,
        "mean_start_minute": s.mean_start_min,
        "mean_end_minute": s.mean_end_min,
        "longest_day": {
            "date": s.longest_day[0].isoformat(),
            "minutes": s.longest_day[1],
        },
        "shortest_day": {
            "date": s.shortest_day[0].isoformat(),
            "minutes": s.shortest_day[1],
        },
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
        "monthly_ok": ig.monthly_ok,
        "total_raw_minutes": ig.total_raw_min,
        "total_segment_minutes": ig.total_segment_min,
        "unsocial_within_baseline_minutes": ig.unsocial_within_baseline_min,
        "warnings": list(ig.warnings),
    }


def _content(result: core.HoursResult, rec) -> dict:
    t = result.totals
    return {
        "period": {
            "start": result.period.start.isoformat(),
            "end": result.period.end.isoformat(),
        },
        "totals": {
            "total_minutes": t.total_min,
            "day_count": t.day_count,
            "week_count": t.week_count,
            "minutes_by_band": _by_band(t.minutes_by_band),
            "minutes_by_class": _by_class(t.minutes_by_class),
            "unsocial_within_baseline_minutes": t.unsocial_within_baseline_min,
            "above_contract_minutes": t.above_contract_min,
        },
        "weekly": _weekly(result.weeks),
        "monthly": _monthly(result.months),
        "daily": _daily(result.days),
        "cross_tab": {b.value: _by_class(result.cross_tab[b]) for b in ThresholdBand},
        "cumulative": [
            {"date": p.date.isoformat(), "cumulative_minutes": p.cumulative_min}
            for p in result.cumulative
        ],
        "statistics": _statistics(result.statistics),
        "payments": _payments(rec),
        "integrity": _integrity(result.integrity),
    }


# --- public API ---
def build_payload(
    result: core.HoursResult,
    *,
    generated_at: datetime | None = None,
    subject: dict | None = None,
    reconciliation=None,
) -> dict:
    """HoursResult -> JSON-ready dict. `content` is pure in `result` and
    `reconciliation`; only `meta.generated_at` varies with time (injectable for
    deterministic tests).

    `reconciliation=None` means "no payments recorded", not "unknown": it
    reconciles against an empty payment list, so the payments block is always
    present and always truthful. That is today's real state, and it keeps one
    shape for the website to render rather than two."""
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)
    if reconciliation is None:
        reconciliation = payments_mod.reconcile(result.weeks, [])
    return {
        "meta": _meta(generated_at, subject),
        "content": _content(result, reconciliation),
    }


def to_json(
    result: core.HoursResult,
    *,
    generated_at: datetime | None = None,
    subject: dict | None = None,
    reconciliation=None,
) -> str:
    payload = build_payload(
        result,
        generated_at=generated_at,
        subject=subject,
        reconciliation=reconciliation,
    )
    # fixed-order dicts already; ensure_ascii=False keeps real characters; trailing newline.
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def write_json(
    result: core.HoursResult,
    path: str,
    *,
    generated_at: datetime | None = None,
    subject: dict | None = None,
    reconciliation=None,
) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            to_json(
                result,
                generated_at=generated_at,
                subject=subject,
                reconciliation=reconciliation,
            )
        )
