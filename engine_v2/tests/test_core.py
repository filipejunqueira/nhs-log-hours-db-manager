"""
test_core.py -- exercises afc_hours/core.py

Synthetic weeks are hand-computed; real-log weeks are re-derived by hand below.
Everything is in MINUTES. Thresholds: 1350 (22.5h), 2250 (37.5h).

Run standalone:  python3 tests/test_core.py
Or with pytest:  pytest tests/test_core.py
"""

import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from afc_hours import core  # noqa: E402
from afc_hours.core import ThresholdBand as TB, UnsocialClass as UC, DayType  # noqa: E402

REAL_LOG = os.environ.get("AFC_REAL_LOG") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "fixtures", "hours_2026-07-14.csv")


# --- helpers ---
def hhmm(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def rd(datestr, start, end, provided=None):
    return core.RawDay(date.fromisoformat(datestr), hhmm(start), hhmm(end), provided)


def bands(res):
    return res.totals.minutes_by_band


def classes(res):
    return res.totals.minutes_by_class


def seg_key(segs):
    return sorted((s.date.isoformat(), s.start_min, s.end_min,
                   s.unsocial_class.value, s.threshold_band.value) for s in segs)


def write_csv(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="")
    f.write(text)
    f.close()
    return f.name


# Mon-Fri of ISO week 23 (2026-06-01 .. 2026-06-05); all daytime unless noted.
MON, TUE, WED, THU, FRI = (f"2026-06-0{n}" for n in range(1, 6))
SAT, SUN = "2026-06-06", "2026-06-07"


# === P1: baseline-first banding at key totals ============================
def test_p1_under_baseline_all_contracted():
    # 2 days x 600 = 1200 min (<1350): all contracted, nothing extra
    res = core.compute([rd(MON, "08:00", "18:00"), rd(TUE, "08:00", "18:00")])
    assert bands(res)[TB.CONTRACTED] == 1200
    assert bands(res)[TB.ADDITIONAL] == 0
    assert bands(res)[TB.OVERTIME] == 0


def test_p1_exact_1350_boundary():
    # 3 x 450 = 1350 exactly: contracted full, no spurious additional, no zero-len seg
    res = core.compute([rd(MON, "08:00", "15:30"), rd(TUE, "08:00", "15:30"),
                        rd(WED, "08:00", "15:30")])
    assert bands(res) == {TB.CONTRACTED: 1350, TB.ADDITIONAL: 0, TB.OVERTIME: 0}
    assert all(s.duration_min > 0 for s in res.segments)


def test_p1_thirty_hours():
    # 1800 min: 1350 contracted + 450 additional, no overtime
    res = core.compute([rd(MON, "08:00", "18:00"), rd(TUE, "08:00", "18:00"),
                        rd(WED, "08:00", "18:00")])
    assert bands(res) == {TB.CONTRACTED: 1350, TB.ADDITIONAL: 450, TB.OVERTIME: 0}


def test_p1_exact_2250_boundary():
    # 5 x 450 = 2250 exactly: 1350 + 900, no overtime
    res = core.compute([rd(d, "08:00", "15:30") for d in (MON, TUE, WED, THU, FRI)])
    assert bands(res) == {TB.CONTRACTED: 1350, TB.ADDITIONAL: 900, TB.OVERTIME: 0}


def test_p1_forty_hours_overtime():
    # 2400 min: 1350 + 900 + 150 overtime
    res = core.compute([rd(d, "08:00", "16:00") for d in (MON, TUE, WED, THU, FRI)])
    assert bands(res) == {TB.CONTRACTED: 1350, TB.ADDITIONAL: 900, TB.OVERTIME: 150}


# === P2: banding is invariant to input row order =========================
def test_p2_row_order_does_not_change_banding():
    days = [rd(d, "08:00", "16:00") for d in (MON, TUE, WED, THU, FRI)]
    a = core.compute(days)
    b = core.compute(list(reversed(days)))
    assert bands(a) == bands(b)
    assert seg_key(a.segments) == seg_key(b.segments)


# === clock classification ================================================
def test_weekday_crossing_2000_splits_day_and_night():
    res = core.compute([rd(MON, "17:00", "21:00")])  # 180 day + 60 night
    assert classes(res)[UC.DAYTIME] == 180
    assert classes(res)[UC.WEEKDAY_NIGHT] == 60


def test_weekday_before_0600_is_night():
    res = core.compute([rd(MON, "05:00", "09:00")])  # 60 night + 180 day
    assert classes(res)[UC.WEEKDAY_NIGHT] == 60
    assert classes(res)[UC.DAYTIME] == 180


def test_boundary_2000_is_night_not_day():
    res = core.compute([rd(MON, "19:00", "20:30")])  # 60 day (19-20) + 30 night (20-20:30)
    assert classes(res)[UC.DAYTIME] == 60
    assert classes(res)[UC.WEEKDAY_NIGHT] == 30


def test_saturday_is_single_wholeday_segment():
    res = core.compute([rd(SAT, "10:00", "14:00")])
    assert classes(res)[UC.SATURDAY] == 240
    assert classes(res)[UC.DAYTIME] == 0
    saturday_segs = [s for s in res.segments if s.date.isoformat() == SAT]
    assert len(saturday_segs) == 1  # no 06:00/20:00 split on a weekend


def test_sunday_is_single_wholeday_segment():
    res = core.compute([rd(SUN, "08:00", "21:00")])  # spans 20:00 but stays one Sunday segment
    assert classes(res)[UC.SUNDAY] == 780
    assert len([s for s in res.segments if s.date.isoformat() == SUN]) == 1


def test_bank_holiday_takes_precedence_over_weekday():
    # 2026-08-31 is the Summer bank holiday, a Monday
    res = core.compute([rd("2026-08-31", "09:00", "17:00")])
    assert res.days[0].day_type is DayType.BANK_HOLIDAY
    assert classes(res)[UC.BANK_HOLIDAY] == 480
    assert classes(res)[UC.DAYTIME] == 0


# === the within-baseline flag ============================================
def test_unsocial_within_baseline_flag_fires():
    # only a Sunday, 240 min (<1350): contracted AND unsocial -> flagged
    res = core.compute([rd(SUN, "09:00", "13:00")])
    assert bands(res)[TB.CONTRACTED] == 240
    assert res.totals.unsocial_within_baseline_min == 240
    assert len(res.weeks[0].flagged_segments) == 1


def test_unsocial_after_baseline_is_not_flagged():
    # fill baseline with weekday daytime, then a Sunday at the end -> NOT flagged
    res = core.compute([rd(MON, "08:00", "18:00"), rd(TUE, "08:00", "18:00"),
                        rd(WED, "08:00", "12:00"), rd(SUN, "09:00", "13:00")])
    # 600+600+240 = 1440 weekday fills baseline (1350) + 90 additional; Sunday 240 -> additional
    assert res.totals.unsocial_within_baseline_min == 0
    assert classes(res)[UC.SUNDAY] == 240


# === ingest guards (hard errors) =========================================
def _expect_error(text, needle):
    path = write_csv(text)
    try:
        core.ingest_csv(path)
    except ValueError as e:
        assert needle in str(e).lower(), f"expected {needle!r} in: {e}"
    else:
        raise AssertionError(f"expected ValueError mentioning {needle!r}")
    finally:
        os.unlink(path)


def test_overnight_is_hard_error():
    _expect_error("Date,Start,End\n2026-06-01,22:00,02:00\n", "overnight")


def test_bank_holiday_year_guard():
    _expect_error("Date,Start,End\n2025-06-02,09:00,17:00\n", "covered")


def test_ambiguous_numeric_date_rejected():
    _expect_error("Date,Start,End\n01/06/2026,09:00,17:00\n", "ambiguous")


def test_incomplete_row_is_hard_error():
    _expect_error("Date,Start,End\n2026-06-01,08:00,\n", "incomplete")


def test_blank_line_is_ignored_not_error():
    path = write_csv("Date,Start,End\n2026-06-01,08:00,16:00\n,,\n")
    try:
        rows = core.ingest_csv(path)
        assert len(rows) == 1
    finally:
        os.unlink(path)


def test_empty_input_raises_clean_error():
    try:
        core.compute([])
    except ValueError as e:
        assert "no working days" in str(e).lower()
    else:
        raise AssertionError("expected ValueError on empty input")


def test_provided_minutes_mismatch_warns_not_fatal():
    res = core.compute([rd(MON, "08:00", "16:00", provided=999)])  # real = 480
    assert any("differs from recomputed" in w for w in res.integrity.warnings)


# === real log: invariants + hand re-derivation ===========================
def _real():
    return core.compute_from_csv(REAL_LOG)


def test_real_log_all_invariants_pass():
    ig = _real().integrity
    assert ig.conservation_ok and ig.partitions_ok and ig.uniqueness_ok
    assert ig.banding_formula_ok and ig.crosstab_ok and ig.span_ok


def test_real_log_grand_totals():
    res = _real()
    assert res.totals.total_min == 16808          # 280.13h
    assert bands(res) == {TB.CONTRACTED: 8528, TB.ADDITIONAL: 4540, TB.OVERTIME: 3740}


def test_real_log_week_w23_hand_derivation():
    # Mon1..Sun7: 537+535+772+794+360+409 = 3407 min
    w = next(w for w in _real().weeks if w.iso_week == "2026-W23")
    assert w.total_min == 3407
    assert w.minutes_by_band == {TB.CONTRACTED: 1350, TB.ADDITIONAL: 900, TB.OVERTIME: 1157}


def test_real_log_week_w24_hand_derivation():
    # Mon8..Sun14: 624+665+539+609+417+544 = 3398 min
    w = next(w for w in _real().weeks if w.iso_week == "2026-W24")
    assert w.total_min == 3398
    assert w.minutes_by_band == {TB.CONTRACTED: 1350, TB.ADDITIONAL: 900, TB.OVERTIME: 1148}


def test_real_log_unsocial_class_totals():
    c = classes(_real())
    assert c[UC.SUNDAY] == 953          # 409 (7 Jun) + 544 (14 Jun)
    assert c[UC.WEEKDAY_NIGHT] == 151   # 54 + 79 + 18 (3rd, 4th, 24th evenings)
    assert c[UC.SATURDAY] == 0
    assert c[UC.BANK_HOLIDAY] == 0
    assert c[UC.DAYTIME] == 16808 - 953 - 151


def test_real_log_no_unsocial_within_baseline():
    # every Sunday/evening falls AFTER the 22.5h baseline in its week -> clean zero
    assert _real().totals.unsocial_within_baseline_min == 0


def test_real_log_iso_weeks_present():
    weeks = {w.iso_week for w in _real().weeks}
    assert weeks == {"2026-W23", "2026-W24", "2026-W25", "2026-W26",
                     "2026-W27", "2026-W28", "2026-W29"}


# === audit fixes: overlap/duplicate (F1), diagnostics (F2/F3/F4), I6 ======
def test_overlapping_periods_rejected():
    _expect_error("Date,Start,End\n2026-06-01,09:00,12:00\n2026-06-01,11:00,14:00\n", "overlap")


def test_contained_period_rejected_as_overlap():
    _expect_error("Date,Start,End\n2026-06-01,09:00,14:00\n2026-06-01,10:00,12:00\n", "overlap")


def test_duplicate_period_rejected():
    _expect_error("Date,Start,End\n2026-06-01,08:00,16:00\n2026-06-01,08:00,16:00\n", "duplicate")


def test_contiguous_periods_allowed():
    path = write_csv("Date,Start,End\n2026-06-01,09:00,12:00\n2026-06-01,12:00,15:00\n")
    try:
        assert len(core.ingest_csv(path)) == 2  # touching endpoints are legal
    finally:
        os.unlink(path)


def test_split_shift_with_gap_allowed():
    path = write_csv("Date,Start,End\n2026-06-01,09:00,12:00\n2026-06-01,14:00,16:00\n")
    try:
        assert len(core.ingest_csv(path)) == 2
    finally:
        os.unlink(path)


def test_zero_length_period_message():
    _expect_error("Date,Start,End\n2026-06-01,09:00,09:00\n", "zero-length")


def test_backwards_same_day_message():
    _expect_error("Date,Start,End\n2026-06-01,17:00,09:00\n", "precedes")


def test_dotted_date_is_unrecognised_format():
    _expect_error("Date,Start,End\n2026.06.01,09:00,17:00\n", "unrecognised")


def test_nonzero_seconds_rejected():
    _expect_error("Date,Start,End\n2026-06-01,08:00:45,17:00\n", "seconds")


def test_zero_seconds_accepted():
    path = write_csv("Date,Start,End\n2026-06-01,08:00:00,17:00:00\n")
    try:
        rows = core.ingest_csv(path)
        assert len(rows) == 1 and rows[0].duration_min == 540
    finally:
        os.unlink(path)


def test_i6_catches_overlap_passed_directly_to_compute():
    # bypass ingest: hand-build overlapping rows; the I6 invariant must fire
    overlapping = [rd(MON, "09:00", "12:00"), rd(MON, "11:00", "14:00")]
    try:
        core.compute(overlapping)
    except AssertionError as e:
        assert "I6" in str(e)
    else:
        raise AssertionError("expected I6 assertion on overlapping rows")


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
