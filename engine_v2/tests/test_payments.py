"""
test_payments.py -- exercises afc_hours/payments.py

Run standalone:  python3 tests/test_payments.py
Or with pytest:  pytest tests/test_payments.py
"""

import os
import sys
import tempfile
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from afc_hours import payments as pay  # noqa: E402
from afc_hours.core import ThresholdBand as TB  # noqa: E402
from afc_hours.core import UnsocialClass as UC  # noqa: E402
from afc_hours.core import WeekSummary  # noqa: E402

HEADER = "Date,MinutesPaid,HoursPaid,Note\n"


def _csv(body, header=HEADER):
    """Write a payments CSV to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(header + body)
    return path


def _week(iso, monday, contracted, additional=0, overtime=0):
    """A WeekSummary carrying only what reconcile() reads."""
    return WeekSummary(
        iso_week=iso,
        monday=monday,
        day_count=5,
        total_min=contracted + additional + overtime,
        minutes_by_band={
            TB.CONTRACTED: contracted,
            TB.ADDITIONAL: additional,
            TB.OVERTIME: overtime,
        },
        minutes_by_class={c: 0 for c in UC},
        unsocial_within_baseline_min=0,
        flagged_segments=(),
    )


# ═══ ingest: the empty cases, which are the ONLY state that exists today ═══
def test_missing_file_is_legal_and_means_no_payments():
    """core.compute() hard-errors on empty input. This must NOT copy that:
    'no payments yet' is the normal state, not a broken file."""
    assert pay.ingest_payments_csv("/nonexistent/payments.csv") == []


def test_header_only_file_is_legal():
    path = _csv("")
    try:
        assert pay.ingest_payments_csv(path) == []
    finally:
        os.unlink(path)


def test_blank_lines_are_ignored():
    path = _csv("\n28-Aug-26,600,10.0,July claim\n\n")
    try:
        assert len(pay.ingest_payments_csv(path)) == 1
    finally:
        os.unlink(path)


# ═══ ingest: parsing ═══
def test_reads_a_payment():
    path = _csv("28-Aug-26,1380,23.0,July claim\n")
    try:
        (p,) = pay.ingest_payments_csv(path)
        assert p.date == date(2026, 8, 28)
        assert p.minutes_paid == 1380
        assert p.note == "July claim"
    finally:
        os.unlink(path)


def test_iso_dates_also_parse():
    path = _csv("2026-08-28,600,10.0,\n")
    try:
        (p,) = pay.ingest_payments_csv(path)
        assert p.date == date(2026, 8, 28)
    finally:
        os.unlink(path)


def test_payment_dates_may_be_outside_the_bank_holiday_years():
    """The hours log refuses a year it has no bank holidays for, because it
    must classify those days. A payment is not classified, and payments run
    into future years, so that restriction must not apply here."""
    path = _csv("2031-01-15,600,10.0,\n")
    try:
        (p,) = pay.ingest_payments_csv(path)
        assert p.date.year == 2031
    finally:
        os.unlink(path)


def test_missing_columns_are_rejected():
    path = _csv("28-Aug-26,600\n", header="Date,Something\n")
    try:
        with pytest.raises(ValueError, match="MinutesPaid"):
            pay.ingest_payments_csv(path)
    finally:
        os.unlink(path)


@pytest.mark.parametrize("minutes", ["0", "-600"])
def test_non_positive_minutes_rejected(minutes):
    path = _csv(f"28-Aug-26,{minutes},1.0,\n")
    try:
        with pytest.raises(ValueError, match="positive"):
            pay.ingest_payments_csv(path)
    finally:
        os.unlink(path)


def test_fractional_minutes_rejected():
    path = _csv("28-Aug-26,600.5,10.0,\n")
    try:
        with pytest.raises(ValueError, match="whole number"):
            pay.ingest_payments_csv(path)
    finally:
        os.unlink(path)


def test_duplicate_row_rejected():
    path = _csv("28-Aug-26,600,10.0,July claim\n28-Aug-26,600,10.0,July claim\n")
    try:
        with pytest.raises(ValueError, match="identical payment"):
            pay.ingest_payments_csv(path)
    finally:
        os.unlink(path)


# ═══ ingest: HoursPaid is a HARD error, unlike the hours log ═══
def test_hours_contradicting_minutes_is_fatal():
    """Deliberately stricter than the hours log, where Minutes/Hours mismatch
    only warns: there Start and End recompute the truth. A payment row has no
    second source, so publishing either number would be guessing at a figure
    somebody is owed."""
    path = _csv("28-Aug-26,1380,30.0,\n")
    try:
        with pytest.raises(ValueError, match="typo"):
            pay.ingest_payments_csv(path)
    finally:
        os.unlink(path)


def test_two_decimal_place_hours_are_accepted():
    """367 min is recorded as 6.12 h and 6.12 * 60 = 367.2. Rounding at two
    decimal places must not be mistaken for a typo."""
    path = _csv("28-Aug-26,367,6.12,\n")
    try:
        (p,) = pay.ingest_payments_csv(path)
        assert p.minutes_paid == 367
    finally:
        os.unlink(path)


def test_absent_hours_column_is_fine():
    path = _csv("28-Aug-26,600,\n", header="Date,MinutesPaid,Note\n")
    try:
        (p,) = pay.ingest_payments_csv(path)
        assert p.minutes_paid == 600
    finally:
        os.unlink(path)


# ═══ ingest: nothing that looks like money reaches a public file ═══
@pytest.mark.parametrize("note", ["paid £400", "$400 received", "€400", "¥400"])
def test_currency_symbols_in_note_rejected(note):
    path = _csv(f"28-Aug-26,600,10.0,{note}\n")
    try:
        with pytest.raises(ValueError, match="currency symbol"):
            pay.ingest_payments_csv(path)
    finally:
        os.unlink(path)


@pytest.mark.parametrize(
    "note", ["salary arrears", "gross adjustment", "net of pension"]
)
def test_money_words_in_note_rejected(note):
    path = _csv(f"28-Aug-26,600,10.0,{note}\n")
    try:
        with pytest.raises(ValueError, match="money word"):
            pay.ingest_payments_csv(path)
    finally:
        os.unlink(path)


@pytest.mark.parametrize("note", ["back pay", "pay run 3", "payslip Aug", "July claim"])
def test_ordinary_notes_are_accepted(note):
    """The guard keeps figures out of a public file; it does not police
    vocabulary. 'pay' states no amount and is the natural word to use."""
    path = _csv(f"28-Aug-26,600,10.0,{note}\n")
    try:
        (p,) = pay.ingest_payments_csv(path)
        assert p.note == note
    finally:
        os.unlink(path)


# ═══ reconcile: the arithmetic ═══
WEEKS = (
    _week("2026-W23", date(2026, 6, 1), 1350, additional=600),  # extra 600
    _week("2026-W24", date(2026, 6, 8), 1350, additional=400),  # extra 400
    _week(
        "2026-W25", date(2026, 6, 15), 1350, additional=900, overtime=100
    ),  # extra 1000
)
TOTAL_EXTRA = 2000


def test_no_payments_everything_is_owed():
    r = pay.reconcile(WEEKS, [])
    assert r.above_contract_min == TOTAL_EXTRA
    assert r.paid_min == 0
    assert r.unpaid_min == TOTAL_EXTRA
    assert r.overpaid_min == 0
    assert r.paid_up_to is None
    assert r.ledger == ()
    assert r.warnings == ()


def test_partial_payment_settles_oldest_week_first():
    r = pay.reconcile(WEEKS, [pay.Payment(date(2026, 7, 1), 700)])
    assert r.paid_min == 700
    assert r.unpaid_min == 1300
    # W23 (600) fully settled, 100 of W24's 400 covered
    assert [(w.iso_week, w.unpaid_min) for w in r.unpaid_weeks] == [
        ("2026-W24", 300),
        ("2026-W25", 1000),
    ]
    assert r.paid_up_to == date(2026, 6, 7)  # the Sunday of W23


def test_exact_payment_clears_everything():
    r = pay.reconcile(WEEKS, [pay.Payment(date(2026, 7, 1), TOTAL_EXTRA)])
    assert r.unpaid_min == 0
    assert r.overpaid_min == 0
    assert r.unpaid_weeks == ()
    assert r.paid_up_to == date(2026, 6, 21)  # Sunday of the last week
    assert r.warnings == ()


def test_overpayment_warns_and_never_goes_negative():
    """A true state of the world (or a sign the log is behind), not a
    contradiction -- so it must remain publishable."""
    r = pay.reconcile(WEEKS, [pay.Payment(date(2026, 7, 1), TOTAL_EXTRA + 500)])
    assert r.unpaid_min == 0
    assert r.overpaid_min == 500
    assert len(r.warnings) == 1
    assert "more paid than accrued" in r.warnings[0]


def test_several_payments_accumulate_in_date_order():
    r = pay.reconcile(
        WEEKS,
        [pay.Payment(date(2026, 8, 1), 400), pay.Payment(date(2026, 7, 1), 300)],
    )
    assert [(e.date, e.minutes_paid, e.cumulative_paid_min) for e in r.ledger] == [
        (date(2026, 7, 1), 300, 300),
        (date(2026, 8, 1), 400, 700),
    ]
    assert r.paid_min == 700


def test_reconcile_is_pure_and_repeatable():
    ps = [pay.Payment(date(2026, 7, 1), 700)]
    assert pay.reconcile(WEEKS, ps) == pay.reconcile(WEEKS, ps)


# ═══ reconcile: paid_up_to, the figure most able to mislead ═══
def test_paid_up_to_is_null_when_nothing_is_paid_even_if_a_week_has_no_extra():
    """A week with no extra hours is trivially 'settled'. Reporting a date
    beside 'paid: 0' would read as though a payment had happened."""
    weeks = (_week("2026-W22", date(2026, 5, 25), 1200),) + WEEKS  # extra 0 first
    r = pay.reconcile(weeks, [])
    assert r.paid_up_to is None


def test_paid_up_to_skips_zero_extra_weeks():
    weeks = (
        _week("2026-W22", date(2026, 5, 25), 1000),  # extra 0
        _week("2026-W23", date(2026, 6, 1), 1350, additional=600),  # extra 600
        _week("2026-W24", date(2026, 6, 8), 1350, additional=400),
    )
    r = pay.reconcile(weeks, [pay.Payment(date(2026, 7, 1), 600)])
    # W22 has nothing to settle, so the answer is W23's Sunday, not W22's
    assert r.paid_up_to == date(2026, 6, 7)


def test_paid_up_to_is_null_when_the_first_owing_week_is_only_part_paid():
    r = pay.reconcile(WEEKS, [pay.Payment(date(2026, 7, 1), 100)])
    assert r.paid_up_to is None
    assert r.unpaid_min == 1900


# ═══ the invariant ═══
@pytest.mark.parametrize("paid", [0, 1, 600, 1999, 2000, 2001, 99999])
def test_I8_reconciliation_balances_at_every_amount(paid):
    ps = [pay.Payment(date(2026, 7, 1), paid)] if paid else []
    r = pay.reconcile(WEEKS, ps)
    assert r.paid_min - r.overpaid_min + r.unpaid_min == r.above_contract_min
    assert r.unpaid_min == max(0, TOTAL_EXTRA - paid)
    assert r.overpaid_min == max(0, paid - TOTAL_EXTRA)
    assert sum(w.unpaid_min for w in r.unpaid_weeks) == r.unpaid_min


def test_above_contract_excludes_the_contracted_band():
    """1350 contracted minutes a week are not owed however much was worked."""
    r = pay.reconcile(WEEKS, [])
    assert r.above_contract_min == TOTAL_EXTRA
    assert sum(w.total_min for w in WEEKS) == TOTAL_EXTRA + 3 * 1350


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
