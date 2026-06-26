"""
core.py -- PART (i): the deterministic hours engine
====================================================

A PURE FUNCTION of the CSV. Same input CSV -> identical output, always.

Contract:
  * Integer MINUTES are the single unit of computation and storage. Hours never
    appear here; they are a front-end display convenience (minutes / 60).
  * No money, no rates, no multipliers. Imports `rules` (the law) and nothing
    money-bearing, so the hours path cannot express a pay rate.
  * No flags. The public `compute(rows)` takes ROWS ONLY -- there is no option
    that can change a single number. This is the structural guarantee that
    "no flag inflates the hours".
  * No rounding (minutes are exact integers), no JSON writing (-> emit.py),
    no rich/logging (-> report/cli), no wall-clock (-> emit.py meta).

Central invariant (the "22.5h before any extra" rule), enforced as a runtime
assertion I4: within each Monday-Sunday pay-week, the first 1350 minutes worked
(in chronological order) are the contracted baseline; only minutes beyond 1350
are additional, and only minutes beyond 2250 are overtime. Unsocial work done
before the baseline is met is still CLASSIFIED strictly, but FLAGGED
(`unsocial_within_baseline`) so the money side can decide whether to claim it.
"""

import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum

from afc_hours import rules


def _fmt_min(m: int) -> str:
    """Minutes-from-midnight -> HH:MM, for error messages."""
    return f"{m // 60:02d}:{m % 60:02d}"

# --- minute constants, derived once from the law (exact integers) ---
CONTRACTED_MIN = round(rules.CONTRACTED_WEEKLY_HOURS * 60)   # 1350
FULLTIME_MIN = round(rules.FULLTIME_WEEKLY_HOURS * 60)       # 2250
DAY_START_MIN = rules.DAY_START.hour * 60 + rules.DAY_START.minute      # 360
NIGHT_START_MIN = rules.NIGHT_START.hour * 60 + rules.NIGHT_START.minute  # 1200


# ─── enums ──────────────────────────────────────────────────────────────────
class DayType(str, Enum):
    WEEKDAY = "weekday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"
    BANK_HOLIDAY = "bank_holiday"


class UnsocialClass(str, Enum):
    DAYTIME = "daytime"                 # weekday 06:00-20:00, no enhancement
    WEEKDAY_NIGHT = "weekday_night"     # weekday 20:00-06:00 (AfC "night")
    SATURDAY = "saturday"
    SUNDAY = "sunday"
    BANK_HOLIDAY = "bank_holiday"


class ThresholdBand(str, Enum):
    CONTRACTED = "contracted"   # 0 - 1350 min
    ADDITIONAL = "additional"   # 1350 - 2250 min
    OVERTIME = "overtime"       # 2250+ min


def _band_dict() -> dict:
    return {b: 0 for b in ThresholdBand}


def _class_dict() -> dict:
    return {c: 0 for c in UnsocialClass}


# ─── model ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RawDay:
    """One validated worked period from the CSV (notes dropped)."""
    date: date
    start_min: int          # minutes from midnight
    end_min: int
    provided_min: int | None = None  # CSV's own Minutes column, if any (for cross-check)

    @property
    def duration_min(self) -> int:
        return self.end_min - self.start_min


@dataclass(frozen=True)
class ClockSegment:
    """A worked piece after clock-boundary splitting; one unsocial class, no band yet."""
    date: date
    start_min: int
    end_min: int
    unsocial_class: UnsocialClass

    @property
    def duration_min(self) -> int:
        return self.end_min - self.start_min


@dataclass(frozen=True)
class Segment:
    """Atomic rate-able unit: exactly one threshold band and one unsocial class."""
    date: date
    start_min: int
    end_min: int
    duration_min: int
    unsocial_class: UnsocialClass
    threshold_band: ThresholdBand


@dataclass(frozen=True)
class FlaggedSegment:
    """An unsocial segment that fell inside the contracted baseline (needs justification)."""
    date: date
    start_min: int
    end_min: int
    duration_min: int
    unsocial_class: UnsocialClass


@dataclass(frozen=True)
class DayRecord:
    date: date
    iso_weekday: int                 # Mon=1 .. Sun=7
    day_type: DayType
    start_min: int                   # earliest start that day
    end_min: int                     # latest end that day
    duration_min: int                # SUM of worked minutes (handles split shifts/gaps)
    minutes_by_class: dict           # UnsocialClass -> minutes


@dataclass(frozen=True)
class WeekSummary:
    iso_week: str                    # e.g. "2026-W23"
    monday: date
    day_count: int
    total_min: int
    minutes_by_band: dict            # ThresholdBand -> minutes
    minutes_by_class: dict           # UnsocialClass -> minutes
    unsocial_within_baseline_min: int
    flagged_segments: tuple          # tuple[FlaggedSegment, ...]


@dataclass(frozen=True)
class CumulativePoint:
    date: date
    cumulative_min: int


@dataclass(frozen=True)
class Period:
    start: date
    end: date


@dataclass(frozen=True)
class Totals:
    total_min: int
    day_count: int
    week_count: int
    minutes_by_band: dict
    minutes_by_class: dict
    unsocial_within_baseline_min: int


@dataclass(frozen=True)
class Statistics:
    pct_by_band: dict                # ThresholdBand -> float (%)
    pct_by_class: dict               # UnsocialClass -> float (%)
    mean_min_per_day: float
    mean_min_per_week: float
    mean_start_min: float
    mean_end_min: float
    longest_day: tuple               # (date, minutes)
    shortest_day: tuple              # (date, minutes)
    days_touching_class: dict        # UnsocialClass -> day count


@dataclass(frozen=True)
class Integrity:
    conservation_ok: bool            # I1
    partitions_ok: bool              # I2
    uniqueness_ok: bool              # I3
    banding_formula_ok: bool         # I4 (the 22.5-first rule)
    crosstab_ok: bool                # I5
    span_ok: bool                    # I6 (per-day worked minutes <= clock span)
    total_raw_min: int
    total_segment_min: int
    unsocial_within_baseline_min: int
    warnings: tuple                  # tuple[str, ...]


@dataclass(frozen=True)
class HoursResult:
    period: Period
    days: tuple
    weeks: tuple
    segments: tuple                  # all atomic Segments (audit trail)
    cross_tab: dict                  # ThresholdBand -> {UnsocialClass -> minutes}
    totals: Totals
    statistics: Statistics
    cumulative: tuple
    integrity: Integrity


# ─── ingest ─────────────────────────────────────────────────────────────────
_MONTH_FORMATS = ("%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%d %B %Y", "%d-%B-%Y")


def _parse_date(s: str, rownum: int) -> date:
    s = s.strip()
    try:
        return date.fromisoformat(s)              # ISO YYYY-MM-DD (preferred)
    except ValueError:
        pass
    for fmt in _MONTH_FORMATS:                     # explicit month names
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    if any(ch.isalpha() for ch in s):
        raise ValueError(f"Row {rownum}: unrecognised date {s!r}")
    # numeric, non-ISO. A slash- or dash-separated numeric date is genuinely
    # ambiguous (DD/MM vs MM/DD); any other separator is just an unsupported format.
    if re.fullmatch(r"\d{1,4}([/-])\d{1,2}\1\d{1,4}", s):
        raise ValueError(
            f"Row {rownum}: ambiguous numeric date {s!r} (day/month order cannot be "
            f"determined). Export dates as ISO YYYY-MM-DD."
        )
    raise ValueError(
        f"Row {rownum}: unrecognised date format {s!r}. Export dates as ISO YYYY-MM-DD."
    )


def _parse_time_to_min(s: str, rownum: int, col: str) -> int:
    s = s.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            t = datetime.strptime(s, fmt).time()
        except ValueError:
            continue
        if t.second:  # times are recorded to the minute; do not silently truncate
            raise ValueError(
                f"Row {rownum}: {col} time {s!r} has non-zero seconds; record times "
                f"to the minute (HH:MM)."
            )
        return t.hour * 60 + t.minute
    raise ValueError(f"Row {rownum}: cannot parse {col} time {s!r} (expected HH:MM)")


def ingest_csv(path: str) -> list:
    """CSV -> list[RawDay]. All validation/guards live here; failures are hard errors."""
    entries: list = []  # (line_number, RawDay)
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        fmap = {h.lower().strip(): h for h in headers}

        def col(*names):
            for nm in names:
                if nm in fmap:
                    return fmap[nm]
            return None

        c_date, c_start, c_end = col("date"), col("start"), col("end")
        c_min = col("minutes", "mins")
        if not (c_date and c_start and c_end):
            raise ValueError("CSV must contain Date, Start and End columns")

        for i, row in enumerate(reader, start=2):  # row 1 is the header
            dval = (row.get(c_date) or "").strip()
            sval = (row.get(c_start) or "").strip()
            eval_ = (row.get(c_end) or "").strip()
            if not dval and not sval and not eval_:
                continue  # fully blank line: ignore
            if not (dval and sval and eval_):
                raise ValueError(
                    f"Row {i}: incomplete entry (Date, Start, End all required); "
                    f"got date={dval!r} start={sval!r} end={eval_!r}"
                )
            d = _parse_date(dval, i)
            if d.year not in rules.BANK_HOLIDAY_YEARS_COVERED:
                raise ValueError(
                    f"Row {i}: date {d.isoformat()} is in year {d.year}, outside the "
                    f"covered years {sorted(rules.BANK_HOLIDAY_YEARS_COVERED)}; extend "
                    f"rules.BANK_HOLIDAYS before classifying it."
                )
            smin = _parse_time_to_min(sval, i, "Start")
            emin = _parse_time_to_min(eval_, i, "End")
            if emin == smin:
                raise ValueError(
                    f"Row {i} ({d.isoformat()}): zero-length period (Start and End are "
                    f"both {sval})."
                )
            if emin < smin:
                raise ValueError(
                    f"Row {i} ({d.isoformat()}): End {eval_} precedes Start {sval} on the "
                    f"same day. If you worked past midnight, split into two rows (one ending "
                    f"23:59 and one starting 00:00); overnight shifts in a single row are not "
                    f"supported. Otherwise correct the times."
                )
            provided = None
            if c_min:
                mv = (row.get(c_min) or "").strip()
                if mv:
                    try:
                        provided = int(round(float(mv)))
                    except ValueError:
                        provided = None
            entries.append((i, RawDay(date=d, start_min=smin, end_min=emin, provided_min=provided)))

    _reject_overlaps(entries)
    return [rd for _, rd in entries]


def _reject_overlaps(entries: list) -> None:
    """Hard-error on same-date periods that overlap or duplicate (touching endpoints are
    allowed, so split and contiguous shifts pass). Sorting by start makes a consecutive
    check sufficient: if any later period overlaps an earlier one, the immediately
    following period does too."""
    by_date: dict = {}
    for lineno, rd in entries:
        by_date.setdefault(rd.date, []).append((lineno, rd))
    for d, items in by_date.items():
        items.sort(key=lambda x: (x[1].start_min, x[1].end_min))
        for (ln_a, a), (ln_b, b) in zip(items, items[1:]):
            if b.start_min < a.end_min:  # strict overlap; equal endpoints are contiguous, OK
                if a.start_min == b.start_min and a.end_min == b.end_min:
                    raise ValueError(
                        f"Rows {ln_a} and {ln_b} ({d.isoformat()}): duplicate period "
                        f"{_fmt_min(a.start_min)}-{_fmt_min(a.end_min)}; remove the repeat."
                    )
                raise ValueError(
                    f"Rows {ln_a} and {ln_b} ({d.isoformat()}): periods overlap "
                    f"({_fmt_min(a.start_min)}-{_fmt_min(a.end_min)} and "
                    f"{_fmt_min(b.start_min)}-{_fmt_min(b.end_min)}); merge or correct them."
                )


# ─── classify ───────────────────────────────────────────────────────────────
def day_type(d: date) -> DayType:
    if d in rules.BANK_HOLIDAYS:
        return DayType.BANK_HOLIDAY
    wd = d.weekday()
    if wd == 5:
        return DayType.SATURDAY
    if wd == 6:
        return DayType.SUNDAY
    return DayType.WEEKDAY


_WHOLEDAY_CLASS = {
    DayType.SATURDAY: UnsocialClass.SATURDAY,
    DayType.SUNDAY: UnsocialClass.SUNDAY,
    DayType.BANK_HOLIDAY: UnsocialClass.BANK_HOLIDAY,
}


def clock_segments(raw: RawDay) -> list:
    """Split a worked period by the 06:00/20:00 weekday boundaries into clock-classified
    pieces. Weekend/bank-holiday days are a single whole-day segment (rules.WHOLE_DAY)."""
    dt = day_type(raw.date)
    if dt is not DayType.WEEKDAY:
        return [ClockSegment(raw.date, raw.start_min, raw.end_min, _WHOLEDAY_CLASS[dt])]

    # weekday: cut at 06:00 and 20:00 where they fall strictly inside the interval
    cuts = sorted({raw.start_min, raw.end_min}
                  | {b for b in (DAY_START_MIN, NIGHT_START_MIN)
                     if raw.start_min < b < raw.end_min})
    out = []
    for a, b in zip(cuts, cuts[1:]):
        # day window is [06:00, 20:00); 20:00 onward and pre-06:00 are night
        is_day = DAY_START_MIN <= a < NIGHT_START_MIN
        cls = UnsocialClass.DAYTIME if is_day else UnsocialClass.WEEKDAY_NIGHT
        out.append(ClockSegment(raw.date, a, b, cls))
    return out


# ─── band ───────────────────────────────────────────────────────────────────
def week_anchor(d: date) -> date:
    """Monday of the pay-week containing d (rules.PAY_WEEK_START_WEEKDAY == Monday)."""
    return d - timedelta(days=(d.weekday() - rules.PAY_WEEK_START_WEEKDAY) % 7)


def _band_for_cumulative(start_cum: int) -> ThresholdBand:
    if start_cum >= FULLTIME_MIN:
        return ThresholdBand.OVERTIME
    if start_cum >= CONTRACTED_MIN:
        return ThresholdBand.ADDITIONAL
    return ThresholdBand.CONTRACTED


def band_week(week_segments: list) -> list:
    """Chronologically attribute a week's clock segments to threshold bands, splitting at
    1350/2250 minutes. Sort is purely temporal so input row order cannot affect banding."""
    ordered = sorted(week_segments, key=lambda s: (s.date, s.start_min))
    atomic: list = []
    cum = 0
    for seg in ordered:
        d = seg.duration_min
        # cumulative range this segment occupies: [cum, cum + d)
        boundaries = sorted({cum, cum + d}
                            | {t for t in (CONTRACTED_MIN, FULLTIME_MIN) if cum < t < cum + d})
        for p0, p1 in zip(boundaries, boundaries[1:]):
            off0, off1 = p0 - cum, p1 - cum
            atomic.append(Segment(
                date=seg.date,
                start_min=seg.start_min + off0,
                end_min=seg.start_min + off1,
                duration_min=p1 - p0,
                unsocial_class=seg.unsocial_class,
                threshold_band=_band_for_cumulative(p0),
            ))
        cum += d
    return atomic


# ─── stats ──────────────────────────────────────────────────────────────────
def _statistics(days: list, total_min: int, by_band: dict, by_class: dict,
                week_count: int) -> Statistics:
    day_count = len(days)
    pct_band = {b: round(by_band[b] / total_min * 100, 2) if total_min else 0.0
                for b in ThresholdBand}
    pct_class = {c: round(by_class[c] / total_min * 100, 2) if total_min else 0.0
                 for c in UnsocialClass}
    longest = max(days, key=lambda r: r.duration_min)
    shortest = min(days, key=lambda r: r.duration_min)
    touch = {c: sum(1 for r in days if r.minutes_by_class.get(c, 0) > 0) for c in UnsocialClass}
    return Statistics(
        pct_by_band=pct_band,
        pct_by_class=pct_class,
        mean_min_per_day=round(total_min / day_count, 1) if day_count else 0.0,
        mean_min_per_week=round(total_min / week_count, 1) if week_count else 0.0,
        mean_start_min=round(sum(r.start_min for r in days) / day_count, 1) if day_count else 0.0,
        mean_end_min=round(sum(r.end_min for r in days) / day_count, 1) if day_count else 0.0,
        longest_day=(longest.date, longest.duration_min),
        shortest_day=(shortest.date, shortest.duration_min),
        days_touching_class=touch,
    )


# ─── invariants ─────────────────────────────────────────────────────────────
def _check_invariants(raw_total: int, weeks: list, atomic: list, days: list,
                      by_band: dict, by_class: dict, cross_tab: dict,
                      warnings: list) -> Integrity:
    seg_total = sum(s.duration_min for s in atomic)

    # I1 conservation (overall + per week)
    conservation = (seg_total == raw_total)
    for w in weeks:
        conservation &= (sum(w.minutes_by_band.values()) == w.total_min)
    assert conservation, f"I1 conservation failed: raw={raw_total} segments={seg_total}"

    # I2 both partitions exhaust the total (overall + per week)
    partitions = (sum(by_band.values()) == seg_total == sum(by_class.values()))
    for w in weeks:
        partitions &= (sum(w.minutes_by_band.values()) == w.total_min
                       == sum(w.minutes_by_class.values()))
    assert partitions, "I2 partition exhaustion failed"

    # I3 uniqueness: every atomic segment is positive and singly-classed (structural)
    uniqueness = all(s.duration_min > 0
                     and isinstance(s.threshold_band, ThresholdBand)
                     and isinstance(s.unsocial_class, UnsocialClass)
                     for s in atomic)
    assert uniqueness, "I3 uniqueness/positivity failed"

    # I4 THE 22.5-first rule, per week, as a computed formula
    banding = True
    for w in weeks:
        t = w.total_min
        expect_c = min(t, CONTRACTED_MIN)
        expect_a = max(0, min(t, FULLTIME_MIN) - CONTRACTED_MIN)
        expect_o = max(0, t - FULLTIME_MIN)
        banding &= (w.minutes_by_band[ThresholdBand.CONTRACTED] == expect_c
                    and w.minutes_by_band[ThresholdBand.ADDITIONAL] == expect_a
                    and w.minutes_by_band[ThresholdBand.OVERTIME] == expect_o)
    assert banding, "I4 banding formula (22.5h-before-extra) failed"

    # I5 cross-tab reconciles to both margins
    crosstab = True
    for b in ThresholdBand:
        crosstab &= (sum(cross_tab[b].values()) == by_band[b])
    for c in UnsocialClass:
        crosstab &= (sum(cross_tab[b][c] for b in ThresholdBand) == by_class[c])
    crosstab &= (sum(cross_tab[b][c] for b in ThresholdBand for c in UnsocialClass) == seg_total)
    assert crosstab, "I5 cross-tab reconciliation failed"

    # I6 per-day worked minutes cannot exceed the clock span (catches overlap/duplicate
    # rows that slipped past ingest, e.g. if compute() is called directly with raw rows)
    span = all(r.duration_min <= r.end_min - r.start_min for r in days)
    assert span, "I6 per-day worked-minutes-exceed-span failed (overlapping/duplicate periods?)"

    ubw = sum(w.unsocial_within_baseline_min for w in weeks)
    return Integrity(
        conservation_ok=conservation, partitions_ok=partitions, uniqueness_ok=uniqueness,
        banding_formula_ok=banding, crosstab_ok=crosstab, span_ok=span,
        total_raw_min=raw_total, total_segment_min=seg_total,
        unsocial_within_baseline_min=ubw, warnings=tuple(warnings),
    )


# ─── api ────────────────────────────────────────────────────────────────────
def compute(rows: list) -> HoursResult:
    """Pure function: list[RawDay] -> HoursResult (minutes only). No options, no flags."""
    if not rows:
        raise ValueError("no working days in input")

    # provided-minutes cross-check -> warnings as DATA (not prints)
    warnings: list = []
    for r in sorted(rows, key=lambda r: (r.date, r.start_min)):
        if r.provided_min is not None and r.provided_min != r.duration_min:
            warnings.append(
                f"{r.date.isoformat()}: CSV Minutes={r.provided_min} differs from "
                f"recomputed {r.duration_min} (recomputed value is authoritative)"
            )

    # clock-classify, group by pay-week, band chronologically
    clocks = [cs for r in rows for cs in clock_segments(r)]
    weeks_map: dict = {}
    for cs in clocks:
        weeks_map.setdefault(week_anchor(cs.date), []).append(cs)

    atomic: list = []
    week_summaries: list = []
    for monday in sorted(weeks_map):
        wsegs = band_week(weeks_map[monday])
        atomic.extend(wsegs)
        by_band = _band_dict()
        by_class = _class_dict()
        flagged: list = []
        for s in wsegs:
            by_band[s.threshold_band] += s.duration_min
            by_class[s.unsocial_class] += s.duration_min
            if s.threshold_band is ThresholdBand.CONTRACTED and s.unsocial_class is not UnsocialClass.DAYTIME:
                flagged.append(FlaggedSegment(s.date, s.start_min, s.end_min,
                                              s.duration_min, s.unsocial_class))
        iy, iw, _ = monday.isocalendar()
        week_summaries.append(WeekSummary(
            iso_week=f"{iy}-W{iw:02d}", monday=monday,
            day_count=len({s.date for s in wsegs}),
            total_min=sum(by_band.values()),
            minutes_by_band=by_band, minutes_by_class=by_class,
            unsocial_within_baseline_min=sum(f.duration_min for f in flagged),
            flagged_segments=tuple(flagged),
        ))

    # day records (aggregate atomic segments by date; handles split shifts)
    by_date: dict = {}
    for s in atomic:
        by_date.setdefault(s.date, []).append(s)
    days: list = []
    for d in sorted(by_date):
        segs = by_date[d]
        mbc = _class_dict()
        for s in segs:
            mbc[s.unsocial_class] += s.duration_min
        days.append(DayRecord(
            date=d, iso_weekday=d.isoweekday(), day_type=day_type(d),
            start_min=min(s.start_min for s in segs),
            end_min=max(s.end_min for s in segs),
            duration_min=sum(s.duration_min for s in segs),
            minutes_by_class=mbc,
        ))

    # overall aggregates
    by_band = _band_dict()
    by_class = _class_dict()
    for s in atomic:
        by_band[s.threshold_band] += s.duration_min
        by_class[s.unsocial_class] += s.duration_min
    total_min = sum(by_band.values())

    cross_tab = {b: _class_dict() for b in ThresholdBand}
    for s in atomic:
        cross_tab[s.threshold_band][s.unsocial_class] += s.duration_min

    # cumulative running total by working day
    cum = 0
    cumulative: list = []
    for r in days:
        cum += r.duration_min
        cumulative.append(CumulativePoint(r.date, cum))

    raw_total = sum(r.duration_min for r in rows)
    integrity = _check_invariants(raw_total, week_summaries, atomic, days,
                                  by_band, by_class, cross_tab, warnings)

    totals = Totals(
        total_min=total_min, day_count=len(days), week_count=len(week_summaries),
        minutes_by_band=by_band, minutes_by_class=by_class,
        unsocial_within_baseline_min=integrity.unsocial_within_baseline_min,
    )
    statistics = _statistics(days, total_min, by_band, by_class, len(week_summaries))
    period = Period(start=min(r.date for r in days), end=max(r.date for r in days))

    return HoursResult(
        period=period, days=tuple(days), weeks=tuple(week_summaries),
        segments=tuple(atomic), cross_tab=cross_tab, totals=totals,
        statistics=statistics, cumulative=tuple(cumulative), integrity=integrity,
    )


def compute_from_csv(path: str) -> HoursResult:
    return compute(ingest_csv(path))
