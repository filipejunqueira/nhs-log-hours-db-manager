"""
test_characterisation.py -- audit characterisation suite for engine_v2 (2026-07-06)
====================================================================================

Companion to /logic-audit_2026-07-06.md. Pins the engine's behaviour on the
FROZEN FIXTURE (tests/fixtures/hours_2026-07-14.csv, 32 days, 1 Jun - 14 Jul 2026)
and on the AUDIT_BRIEF.md section-3 scenarios not already covered by the
engine's own 67 checks.

Lives OUTSIDE engine_v2/ because that package is locked (deny-listed in
.claude/settings.json); this suite imports it read-only.

Tests named test_defect_* pin CURRENT behaviour that the audit report flags as
a defect -- they pass today and exist so any future fix shows up as a
deliberate, visible change here.

Run standalone:  python3 audit/test_characterisation.py
Or with pytest:  pytest audit/
"""

import codecs
import os
import sys
import tempfile
from datetime import date, datetime, timezone

_ENGINE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine_v2"
)
sys.path.insert(0, _ENGINE)
from afc_hours import core, emit  # noqa: E402
from afc_hours.core import ThresholdBand as TB, UnsocialClass as UC, DayType  # noqa: E402

REAL_LOG = os.environ.get("AFC_REAL_LOG") or os.path.join(
    _ENGINE, "tests", "fixtures", "hours_2026-07-14.csv"
)


# --- helpers (same style as engine_v2/tests/test_core.py) ---
def hhmm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def rd(datestr, start, end, provided=None):
    return core.RawDay(date.fromisoformat(datestr), hhmm(start), hhmm(end), provided)


def bands(res):
    return res.totals.minutes_by_band


def classes(res):
    return res.totals.minutes_by_class


def write_csv(text, binary=False):
    mode = "wb" if binary else "w"
    kw = {} if binary else {"newline": ""}
    f = tempfile.NamedTemporaryFile(mode, suffix=".csv", delete=False, **kw)
    f.write(text)
    f.close()
    return f.name


MON, TUE, WED, THU, FRI = (f"2026-06-0{n}" for n in range(1, 6))
SAT, SUN = "2026-06-06", "2026-06-07"


# === real log (current CSV): grand totals ================================
def _real():
    return core.compute_from_csv(REAL_LOG)


def test_real_log_grand_totals_current():
    res = _real()
    assert res.totals.total_min == 16808  # 280.13h, 1 Jun - 14 Jul 2026
    assert res.totals.day_count == 32
    assert res.totals.week_count == 7
    assert bands(res) == {TB.CONTRACTED: 8528, TB.ADDITIONAL: 4540, TB.OVERTIME: 3740}


def test_real_log_weekly_totals_hand_derived():
    # Hand-summed from the CSV, row by row:
    # W23 (1-7 Jun):   537+535+772+794+360+409       = 3407
    # W24 (8-14 Jun):  624+665+539+609+417+544       = 3398
    # W25 (15-19 Jun): 579+554+516+527+379           = 2555
    # W26 (22-26 Jun): 586+642+757+574+700           = 3259
    # W27 (29 Jun-3 Jul): 448+522+566+398+437        = 2371
    # W28 (6-10 Jul):  515+480+225+170               = 1390
    # W29 (14 Jul):    428                           = 428
    expect = {
        "2026-W23": 3407,
        "2026-W24": 3398,
        "2026-W25": 2555,
        "2026-W26": 3259,
        "2026-W27": 2371,
        "2026-W28": 1390,
        "2026-W29": 428,
    }
    got = {w.iso_week: w.total_min for w in _real().weeks}
    assert got == expect
    assert sum(expect.values()) == 16808


def test_real_log_weekly_bands_hand_derived():
    # W23-W27 exceed 2250: 1350 contracted + 900 additional + overtime
    # (total - 2250): 1157, 1148, 305, 1009, 121. W28 (1390) stops at
    # 1350 + 40 additional; W29 (428) is all contracted.
    expect = {
        "2026-W23": {TB.CONTRACTED: 1350, TB.ADDITIONAL: 900, TB.OVERTIME: 1157},
        "2026-W24": {TB.CONTRACTED: 1350, TB.ADDITIONAL: 900, TB.OVERTIME: 1148},
        "2026-W25": {TB.CONTRACTED: 1350, TB.ADDITIONAL: 900, TB.OVERTIME: 305},
        "2026-W26": {TB.CONTRACTED: 1350, TB.ADDITIONAL: 900, TB.OVERTIME: 1009},
        "2026-W27": {TB.CONTRACTED: 1350, TB.ADDITIONAL: 900, TB.OVERTIME: 121},
        "2026-W28": {TB.CONTRACTED: 1350, TB.ADDITIONAL: 40, TB.OVERTIME: 0},
        "2026-W29": {TB.CONTRACTED: 428, TB.ADDITIONAL: 0, TB.OVERTIME: 0},
    }
    for w in _real().weeks:
        assert w.minutes_by_band == expect[w.iso_week]


def test_real_log_class_totals_current():
    c = classes(_real())
    # weekday_night: 3 Jun 20:00-20:54 (54) + 4 Jun 20:00-21:19 (79) + 24 Jun 20:00-20:18 (18)
    # sunday: 7 Jun 409 + 14 Jun 544
    assert c[UC.WEEKDAY_NIGHT] == 54 + 79 + 18 == 151
    assert c[UC.SUNDAY] == 409 + 544 == 953
    assert c[UC.SATURDAY] == 0
    assert c[UC.BANK_HOLIDAY] == 0
    assert c[UC.DAYTIME] == 16808 - 953 - 151 == 15704


def test_real_log_integrity_and_baseline_flag():
    res = _real()
    ig = res.integrity
    assert ig.conservation_ok and ig.partitions_ok and ig.uniqueness_ok
    assert ig.banding_formula_ok and ig.crosstab_ok and ig.span_ok
    assert ig.total_raw_min == ig.total_segment_min == 16808
    assert ig.warnings == ()
    assert res.totals.unsocial_within_baseline_min == 0


def test_real_log_cumulative_series():
    cum = _real().cumulative
    assert len(cum) == 32
    assert cum[-1].cumulative_min == 16808
    assert all(a.cumulative_min < b.cumulative_min for a, b in zip(cum, cum[1:]))


def test_real_log_row_order_invariance():
    with open(REAL_LOG, encoding="utf-8") as f:
        lines = f.read().splitlines()
    path = write_csv("\n".join(lines[:1] + list(reversed(lines[1:]))) + "\n")
    try:
        a, b = _real(), core.compute_from_csv(path)
        assert a.totals == b.totals
        key = lambda r: sorted(
            (
                s.date,
                s.start_min,
                s.end_min,  # noqa: E731
                s.threshold_band,
                s.unsocial_class,
            )
            for s in r.segments
        )
        assert key(a) == key(b)
    finally:
        os.unlink(path)


def test_real_log_emit_content_is_deterministic():
    pin = datetime(2026, 7, 6, tzinfo=timezone.utc)
    assert emit.to_json(_real(), generated_at=pin) == emit.to_json(
        _real(), generated_at=pin
    )


# === threshold straddles inside a single period ==========================
def test_period_straddling_1350_splits_at_exact_minute():
    # 600+600 = 1200 before Wednesday; 1350 is reached 150 min into Wed 08:00-18:00
    res = core.compute([rd(d, "08:00", "18:00") for d in (MON, TUE, WED)])
    wed = [
        (core._fmt_min(s.start_min), core._fmt_min(s.end_min), s.threshold_band)
        for s in res.segments
        if s.date == date(2026, 6, 3)
    ]
    assert wed == [("08:00", "10:30", TB.CONTRACTED), ("10:30", "18:00", TB.ADDITIONAL)]


def test_period_straddling_2250_splits_at_exact_minute():
    # Mon-Thu 08:00-17:20 = 4 x 560 = 2240; Friday 08:00-08:20 crosses 2250 at 08:10
    res = core.compute(
        [rd(d, "08:00", "17:20") for d in (MON, TUE, WED, THU)]
        + [rd(FRI, "08:00", "08:20")]
    )
    assert bands(res) == {TB.CONTRACTED: 1350, TB.ADDITIONAL: 900, TB.OVERTIME: 10}
    fri = [
        (core._fmt_min(s.start_min), core._fmt_min(s.end_min), s.threshold_band)
        for s in res.segments
        if s.date == date(2026, 6, 5)
    ]
    assert fri == [("08:00", "08:10", TB.ADDITIONAL), ("08:10", "08:20", TB.OVERTIME)]


# === clock boundaries: one-minute segments ================================
def test_one_minute_boundary_segments():
    for start, end, expect in (
        ("19:59", "20:00", UC.DAYTIME),
        ("20:00", "20:01", UC.WEEKDAY_NIGHT),
        ("05:59", "06:00", UC.WEEKDAY_NIGHT),
        ("06:00", "06:01", UC.DAYTIME),
    ):
        res = core.compute([rd(MON, start, end)])
        assert classes(res)[expect] == 1, f"{start}-{end} should be {expect.value}"


def test_maximal_day_with_midnight_values():
    # 00:00-23:59 weekday: 06:00-20:00 daytime (840) + 00:00-06:00 and 20:00-23:59 night (599)
    res = core.compute([rd(MON, "00:00", "23:59")])
    assert res.totals.total_min == 1439
    assert classes(res)[UC.DAYTIME] == 840
    assert classes(res)[UC.WEEKDAY_NIGHT] == 599


def test_weekday_spanning_both_boundaries():
    # 05:00-22:00: 60 night + 840 day + 120 night -> three segments
    res = core.compute([rd(MON, "05:00", "22:00")])
    assert classes(res)[UC.DAYTIME] == 840
    assert classes(res)[UC.WEEKDAY_NIGHT] == 180
    assert len(res.segments) == 3


# === day type: 2027 substitute days and adjacency ========================
def test_2027_christmas_substitutes():
    # 25 Dec 2027 is a Saturday; observed 27th (Mon) and Boxing Day on 28th (Tue)
    for d, expect in (
        ("2027-12-25", DayType.SATURDAY),
        ("2027-12-27", DayType.BANK_HOLIDAY),
        ("2027-12-28", DayType.BANK_HOLIDAY),
    ):
        res = core.compute([rd(d, "09:00", "17:00")])
        assert res.days[0].day_type is expect, d


def test_weekend_adjacent_to_bank_holiday_keeps_own_class():
    # Sat 23 May 2026 sits next to the Spring bank holiday (Mon 25 May)
    res = core.compute(
        [rd("2026-05-23", "09:00", "13:00"), rd("2026-05-25", "09:00", "13:00")]
    )
    c = classes(res)
    assert c[UC.SATURDAY] == 240 and c[UC.BANK_HOLIDAY] == 240


def test_good_friday_weekday_bank_holiday():
    res = core.compute([rd("2026-04-03", "09:00", "17:00")])
    assert res.days[0].day_type is DayType.BANK_HOLIDAY
    assert classes(res)[UC.BANK_HOLIDAY] == 480


# === pay-week grouping ====================================================
def test_sunday_and_next_monday_are_different_pay_weeks():
    res = core.compute([rd(SUN, "10:00", "12:00"), rd("2026-06-08", "10:00", "12:00")])
    assert [w.iso_week for w in res.weeks] == ["2026-W23", "2026-W24"]
    assert [w.total_min for w in res.weeks] == [120, 120]


def test_gap_week_not_counted_in_denominators():
    # work in W23 and W25 only; means are over the 2 recorded weeks, not 3 calendar weeks
    res = core.compute([rd(MON, "08:00", "18:00"), rd("2026-06-15", "08:00", "18:00")])
    assert res.totals.week_count == 2
    assert res.statistics.mean_min_per_week == 600.0


def test_partial_first_week_bands_from_zero():
    # a lone Friday start: banding begins at 0 for that week regardless of weekday
    res = core.compute([rd(FRI, "08:00", "18:00")])
    assert bands(res) == {TB.CONTRACTED: 600, TB.ADDITIONAL: 0, TB.OVERTIME: 0}


# === within-baseline flag: mixed week =====================================
def test_mixed_week_flags_only_pre_baseline_unsocial():
    # Mon 19:00-21:00 -> 60 night falls inside baseline (flagged);
    # Tue+Wed fill past 1350; Sunday afterwards is NOT flagged.
    res = core.compute(
        [
            rd(MON, "19:00", "21:00"),
            rd(TUE, "08:00", "19:00"),
            rd(WED, "08:00", "19:00"),
            rd(SUN, "09:00", "13:00"),
        ]
    )
    w = res.weeks[0]
    assert w.unsocial_within_baseline_min == 60
    assert [(f.unsocial_class, f.duration_min) for f in w.flagged_segments] == [
        (UC.WEEKDAY_NIGHT, 60)
    ]


# === ingest: scenarios not covered by the engine's own tests =============
def test_bom_file_is_handled():
    path = write_csv(
        codecs.BOM_UTF8 + b"Date,Start,End\n2026-06-01,08:00,16:00\n", binary=True
    )
    try:
        rows = core.ingest_csv(path)
        assert len(rows) == 1 and rows[0].duration_min == 480
    finally:
        os.unlink(path)


def test_many_short_periods_on_one_date():
    starts = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00"]
    body = "".join(f"2026-06-01,{s},{s[:3]}30\n" for s in starts)  # 6 x 30 min
    path = write_csv("Date,Start,End\n" + body)
    try:
        res = core.compute(core.ingest_csv(path))
        assert res.days[0].duration_min == 180
        assert res.integrity.span_ok
    finally:
        os.unlink(path)


def test_two_digit_year_month_name_dates_accepted():
    # the real CSV uses e.g. '1-Jun-26'; parsed via %d-%b-%y (AUDIT_BRIEF documents
    # only 4-digit forms -- divergence noted in the report). Out-of-range 2-digit
    # years still die at the year guard.
    assert core._parse_date("1-Jun-26", 2) == date(2026, 6, 1)
    path = write_csv("Date,Start,End\n1-Jun-99,09:00,17:00\n")
    try:
        core.ingest_csv(path)
    except ValueError as e:
        assert "covered" in str(e)
    else:
        raise AssertionError("expected year-guard error for 1999")
    finally:
        os.unlink(path)


def test_single_day_statistics():
    res = core.compute([rd(MON, "08:00", "16:00")])
    st = res.statistics
    assert st.mean_min_per_day == 480.0 and st.mean_min_per_week == 480.0
    assert st.longest_day == st.shortest_day == (date(2026, 6, 1), 480)


def test_negative_minutes_value_warns():
    res = core.compute([rd(MON, "08:00", "16:57", provided=-100)])
    assert any("differs from recomputed" in w for w in res.integrity.warnings)


# === defect pins (see logic-audit_2026-07-06.md; these PASS today) ========
def test_minutes_inf_ingests_cleanly_after_f2():
    # D1 (FIXED by F2, then reshaped by F4, 2026-07-19): 'inf' in the optional
    # Minutes column used to crash ingest with an uncaught OverflowError.
    # Ingest now keeps the raw float, so 'inf' ingests cleanly and surfaces as
    # a non-fatal mismatch warning from the cross-check.
    path = write_csv("Date,Start,End,Minutes\n2026-06-01,08:00,16:57,inf\n")
    try:
        rows = core.ingest_csv(path)
        assert len(rows) == 1
        assert rows[0].provided_min == float("inf")
        res = core.compute(rows)
        assert any("differs from recomputed" in w for w in res.integrity.warnings)
    finally:
        os.unlink(path)


def test_non_numeric_minutes_warns_after_f4():
    # D2 (FIXED by F4, 2026-07-19): a non-numeric Minutes value used to be
    # dropped without any warning. It is now kept as the raw string and the
    # skipped cross-check is reported as a non-fatal warning.
    path = write_csv("Date,Start,End,Minutes\n2026-06-01,08:00,16:57,abc\n")
    try:
        rows = core.ingest_csv(path)
        assert rows[0].provided_min == "abc"
        ws = core.compute(rows).integrity.warnings
        assert any("not numeric" in w for w in ws)
    finally:
        os.unlink(path)


def test_fractional_minutes_mismatch_warns_after_f4():
    # D2b (FIXED by F4, 2026-07-19): the cross-check now compares the raw
    # float against the recomputed integer, so Minutes=537.4 against a true
    # 537 warns just like 537.6 does; sub-half-minute discrepancies are
    # visible. An exact "537.0" still matches silently.
    for mv, warns in (("537.4", 1), ("537.6", 1), ("537.0", 0), ("537", 0)):
        path = write_csv(f"Date,Start,End,Minutes\n2026-06-01,08:00,16:57,{mv}\n")
        try:
            res = core.compute(core.ingest_csv(path))
            assert len(res.integrity.warnings) == warns, mv
        finally:
            os.unlink(path)


def test_i6_catches_duplicate_that_fits_within_span_after_f3():
    # D3 (FIXED by F3, 2026-07-19): bypassing ingest, a duplicated period plus
    # a long later period used to pass ALL invariants (worked 840 <= span 840)
    # while double-counting 60 minutes. I6 now also checks pairwise per-day
    # non-overlap of the raw rows, so this fires.
    sneaky = [
        rd(MON, "09:00", "10:00"),
        rd(MON, "09:00", "10:00"),
        rd(MON, "11:00", "23:00"),
    ]
    try:
        core.compute(sneaky)
    except AssertionError as e:
        assert "I6" in str(e)
    else:
        raise AssertionError("expected I6 assertion on padded duplicate rows")


if __name__ == "__main__":
    funcs = [
        v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)
    ]
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
