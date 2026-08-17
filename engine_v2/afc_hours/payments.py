"""
payments.py -- PART (i-b): what payroll has settled, and what is still owed
===========================================================================

`core` answers "how many extra hours were worked". This answers "how many of
them have been paid for", so the page can show the difference. Without it
nobody -- not HR, not the user -- can tell how many extra hours are actually
outstanding, only how many were ever worked.

Contract:
  * MINUTES ONLY, exactly like core. This records how many minutes of extra
    work have been SETTLED. It never records, or knows, at what price.
    The token "money" does not appear in the emitted path (a test enforces it).
  * SEPARATE FROM core.compute() BY DESIGN. compute() takes rows only -- its
    docstring calls that "the structural guarantee that no flag inflates the
    hours". Payments must therefore never become an argument to it; the
    subtraction lives here instead, downstream of a finished HoursResult.
  * reconcile() IS A PURE FUNCTION of (weeks, payments). No I/O, no wall-clock.
  * NOTES NEVER REACH THE OUTPUT, structurally. The CSV's Note column exists
    for the human reading the spreadsheet. `Payment` carries it; `LedgerEntry`
    -- the only payment type that emit sees -- HAS NO NOTE FIELD, so a note
    cannot be serialised even by mistake. core drops the hours log's notes for
    the same reason (see RawDay: "notes dropped").

Attribution rule: a payment settles the OLDEST unpaid pay-week first. This
keeps spreadsheet entry trivial -- no deciding which weeks a payment covers --
and the headline figure (total owed) is independent of the ordering anyway.
"""

import csv
import os
import re
from dataclasses import dataclass
from datetime import date, timedelta

from afc_hours.core import ThresholdBand, _parse_date

# The hours log's own Minutes/Hours cross-check tolerates 2-decimal-place
# rounding: 367 min is recorded as 6.12 h, and 6.12 * 60 = 367.2. Half a
# minute admits that rounding while still catching a real typo.
_HOURS_TOLERANCE_MIN = 0.5

# Deliberately WIDER than test_emit.py's guard, which only looks for "£" and
# "gbp". A note is free text written by a human and the repo is public, so the
# check that runs at ingest must be stronger than the one that checks the
# output, not equal to it.
_MONEY_TOKENS = frozenset(
    {
        "salary",
        "gbp",
        "wage",
        "wages",
        "rate",
        "rates",
        "multiplier",
        "pension",
        "premium",
        "cost",
        "money",
        "gross",
        "net",
    }
)
# "pay" is deliberately ABSENT: "back pay", "pay run" and "payslip Aug" are the
# natural way to describe a claim and state no amount. The guard exists to keep
# figures out of a public file, not to police vocabulary.
_CURRENCY_CHARS = "£$€¥"


@dataclass(frozen=True)
class Payment:
    """One settlement event, as read from the spreadsheet. `note` stops here."""

    date: date
    minutes_paid: int
    note: str = ""


@dataclass(frozen=True)
class LedgerEntry:
    """A payment as the website sees it. No note field, on purpose (see module docstring)."""

    date: date
    minutes_paid: int
    cumulative_paid_min: int


@dataclass(frozen=True)
class WeekSettlement:
    iso_week: str
    monday: date
    extra_min: int  # minutes above contract accrued that week
    paid_min: int  # of those, how many are settled
    unpaid_min: int  # extra_min - paid_min


@dataclass(frozen=True)
class Reconciliation:
    above_contract_min: int
    paid_min: int
    unpaid_min: int
    overpaid_min: int
    paid_up_to: date | None
    ledger: tuple  # tuple[LedgerEntry, ...], date order
    unpaid_weeks: tuple  # tuple[WeekSettlement, ...], only those still owing
    warnings: tuple


# ─── ingest ─────────────────────────────────────────────────────────────────
def _check_note(note: str, rownum: int) -> None:
    """Refuse anything that would put a pay figure on a public page."""
    for ch in _CURRENCY_CHARS:
        if ch in note:
            raise ValueError(
                f"Row {rownum}: Note contains the currency symbol {ch!r}. This file is "
                f"committed to a public repository and the site shows hours only; record "
                f"amounts in the payslip, not here."
            )
    tokens = {t for t in re.split(r"[^a-z]+", note.lower()) if t}
    bad = sorted(_MONEY_TOKENS & tokens)
    if bad:
        raise ValueError(
            f"Row {rownum}: Note contains the money word {bad[0]!r}. This file is committed "
            f"to a public repository and the site shows hours only; describe the claim "
            f'("July claim"), not the amount.'
        )


def _parse_minutes(value: str, rownum: int) -> int:
    try:
        num = float(value)
    except ValueError:
        raise ValueError(
            f"Row {rownum}: MinutesPaid {value!r} is not a number"
        ) from None
    if num != int(num):
        raise ValueError(
            f"Row {rownum}: MinutesPaid {value!r} is not a whole number of minutes"
        )
    minutes = int(num)
    if minutes <= 0:
        raise ValueError(
            f"Row {rownum}: MinutesPaid must be a positive number of minutes, got {minutes}. "
            f"A correction that reduces hours owed belongs in the hours log, not here."
        )
    return minutes


def ingest_payments_csv(path: str) -> list:
    """CSV -> list[Payment]. A MISSING FILE IS LEGAL and means no payments yet --
    today's state, and the reason this cannot copy core.compute()'s
    "no working days in input" hard error. A header-only file is equally legal."""
    if not os.path.exists(path):
        return []

    payments: list = []
    seen: dict = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        fmap = {h.lower().strip(): h for h in headers}

        def col(*names):
            for nm in names:
                if nm in fmap:
                    return fmap[nm]
            return None

        c_date = col("date")
        c_min = col("minutespaid", "minutes_paid", "minutes")
        c_hours = col("hourspaid", "hours_paid", "hours")
        c_note = col("note", "notes")
        if not (c_date and c_min):
            raise ValueError(
                "Payments CSV must contain Date and MinutesPaid columns "
                "(expected header: Date,MinutesPaid,HoursPaid,Note)"
            )

        for i, row in enumerate(reader, start=2):
            dval = (row.get(c_date) or "").strip()
            mval = (row.get(c_min) or "").strip()
            if not dval and not mval:
                continue  # fully blank line: ignore
            if not (dval and mval):
                raise ValueError(
                    f"Row {i}: incomplete payment (Date and MinutesPaid are both "
                    f"required); got date={dval!r} minutes={mval!r}"
                )
            d = _parse_date(dval, i)  # shared parser; no bank-holiday-year
            minutes = _parse_minutes(
                mval, i
            )  # limit here -- payments run into future years
            note = (row.get(c_note) or "").strip() if c_note else ""
            _check_note(note, i)

            # HoursPaid disagreeing with MinutesPaid is FATAL, unlike the hours
            # log where a Minutes mismatch only warns. There, Start and End
            # recompute the truth, so the mismatch is resolvable. Here there is
            # no second source: one of the two numbers is mistyped and nothing
            # can say which, so publishing either would be guessing at a figure
            # someone is owed.
            if c_hours:
                hval = (row.get(c_hours) or "").strip()
                if hval:
                    try:
                        hours = float(hval)
                    except ValueError:
                        raise ValueError(
                            f"Row {i}: HoursPaid {hval!r} is not a number"
                        ) from None
                    if abs(hours * 60 - minutes) > _HOURS_TOLERANCE_MIN:
                        raise ValueError(
                            f"Row {i}: HoursPaid {hval} is {hours * 60:.1f} minutes, but "
                            f"MinutesPaid says {minutes}. One of them is a typo and nothing "
                            f"here can tell which; correct the row."
                        )

            key = (d, minutes, note)
            if key in seen:
                raise ValueError(
                    f"Rows {seen[key]} and {i}: identical payment ({d.isoformat()}, "
                    f"{minutes} min, note {note!r}). If both are real, tell them apart in "
                    f"the Note; otherwise remove the repeat."
                )
            seen[key] = i
            payments.append(Payment(date=d, minutes_paid=minutes, note=note))

    return payments


# ─── reconcile ──────────────────────────────────────────────────────────────
def _extra_min(week) -> int:
    """Minutes above the contracted baseline. Deliberately NOT including
    unsocial_within_baseline_min: those minutes sit inside the contracted 22.5
    hours, so they are not "extra" however they are enhanced."""
    return (
        week.minutes_by_band[ThresholdBand.ADDITIONAL]
        + week.minutes_by_band[ThresholdBand.OVERTIME]
    )


def reconcile(weeks, payments: list) -> Reconciliation:
    """(weeks, payments) -> Reconciliation. Pure. Oldest unpaid week settles first."""
    ordered = sorted(payments, key=lambda p: (p.date, p.minutes_paid))
    paid_total = sum(p.minutes_paid for p in ordered)

    ledger: list = []
    running = 0
    for p in ordered:
        running += p.minutes_paid
        ledger.append(
            LedgerEntry(
                date=p.date, minutes_paid=p.minutes_paid, cumulative_paid_min=running
            )
        )

    settlements: list = []
    pool = paid_total
    for w in sorted(weeks, key=lambda w: w.monday):
        extra = _extra_min(w)
        applied = min(pool, extra)
        pool -= applied
        settlements.append(
            WeekSettlement(
                iso_week=w.iso_week,
                monday=w.monday,
                extra_min=extra,
                paid_min=applied,
                unpaid_min=extra - applied,
            )
        )

    above = sum(s.extra_min for s in settlements)
    unpaid = sum(s.unpaid_min for s in settlements)
    overpaid = pool  # whatever the weeks could not absorb

    # paid_up_to: the naive reading ("last fully-settled week") calls a week
    # with no extra hours settled, which would print a date beside "paid: 0"
    # and read as though a payment had happened. Weeks with extra == 0 are
    # therefore skipped, and nothing paid at all means nothing to report.
    paid_up_to = None
    if paid_total > 0:
        for s in settlements:
            if s.unpaid_min > 0:
                break
            if s.extra_min > 0:
                paid_up_to = s.monday + timedelta(days=6)  # the Sunday

    warnings: list = []
    if overpaid > 0:
        warnings.append(
            f"payments total {paid_total} minutes but only {above} minutes above contract "
            f"have been recorded ({overpaid} more paid than accrued) -- either the hours "
            f"log is behind, or a payment was recorded twice"
        )

    # I8. Assertions, not returned flags: a wrong owed figure must stop the
    # run, never be published with a false-looking tick beside it.
    assert unpaid == max(0, above - paid_total), "I8 unpaid is not accrued - paid"
    assert overpaid == max(0, paid_total - above), "I8 overpaid is not paid - accrued"
    assert paid_total - overpaid + unpaid == above, "I8 reconciliation does not balance"
    assert sum(s.unpaid_min for s in settlements if s.unpaid_min > 0) == unpaid, (
        "I8 per-week unpaid does not sum to the total"
    )

    return Reconciliation(
        above_contract_min=above,
        paid_min=paid_total,
        unpaid_min=unpaid,
        overpaid_min=overpaid,
        paid_up_to=paid_up_to,
        ledger=tuple(ledger),
        unpaid_weeks=tuple(s for s in settlements if s.unpaid_min > 0),
        warnings=tuple(warnings),
    )
