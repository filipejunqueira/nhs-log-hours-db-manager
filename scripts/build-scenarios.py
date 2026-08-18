"""Build the six scenario files the rendered-page check runs against.

    python3 scripts/build-scenarios.py

Writes website/scripts/scenarios/*.json. Run it when the schema changes and the
committed scenarios start failing check-render.mjs -- that failure is the signal
they have gone stale, not a bug in the page.

NOTHING IS WRITTEN INSIDE engine_v2/. The engine is called in memory and the
payment CSVs go to a temporary directory, so this never dirties web_data.json or
touches the locked directory. Do not "simplify" it into dropping a payments.csv
into engine_v2/data/ and running regen.sh.

Output is byte-stable: generated_at is taken from the committed web_data.json
rather than the clock, so re-running produces no diff.
"""

import datetime
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ENGINE = os.path.join(REPO, "engine_v2")
OUT = os.path.join(REPO, "website", "scripts", "scenarios")
HOURS_CSV = "data/filipe_working_hours_log.csv"

sys.path.insert(0, ENGINE)
os.chdir(ENGINE)
from afc_hours import core, emit, payments  # noqa: E402

# Two payments summing to 5400 minutes. That total is not arbitrary: it
# reproduces the case hand-checked in the sandbox on 2026-08-10 -- owed 8793,
# paid_up_to 2026-06-21, W26 left holding 1819. reconcile() derives every one of
# those from the WEEKS, not from the payment dates, so the dates below are free
# choices and only the total matters. See PLAN.md section 7.
PARTIAL_CSV = (
    "Date,MinutesPaid,HoursPaid,Note\n"
    "15-Jul-26,3000,50.00,July claim\n"
    "14-Aug-26,2400,40.00,August claim\n"
)

# More paid than accrued (14193). Renders the overpayment block and the engine's
# own warning, neither of which any other scenario reaches.
OVERPAID_CSV = "Date,MinutesPaid,HoursPaid,Note\n14-Aug-26,15000,250.00,recorded twice by mistake\n"


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(ENGINE, "web_data.json"), encoding="utf-8") as f:
        real = json.load(f)
    stamp = datetime.datetime.strptime(
        real["meta"]["generated_at"], "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=datetime.timezone.utc)

    result = core.compute_from_csv(HOURS_CSV)

    with tempfile.TemporaryDirectory() as tmp:

        def build(name: str, csv_text: str | None) -> dict:
            """Engine output for a payments CSV. None means no payments file."""
            if csv_text is None:
                paid = []
            else:
                path = os.path.join(tmp, f"{name}.csv")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(csv_text)
                paid = payments.ingest_payments_csv(path)
            out = os.path.join(OUT, f"scenario-{name}.json")
            emit.write_json(
                result,
                out,
                generated_at=stamp,
                reconciliation=payments.reconcile(result.weeks, paid),
            )
            with open(out, encoding="utf-8") as f:
                return json.load(f)

        # The control proves the builder before it builds anything: with no
        # payments the emitted payload must equal the committed web_data.json.
        # If it does not, this script and regen.sh disagree and every scenario
        # below is suspect.
        control_path = os.path.join(OUT, "scenario-control.json")
        identical = build("control", None) == real
        os.remove(control_path)
        print(f"control payload == committed web_data.json: {identical}")
        if not identical:
            sys.exit("STOP: this build does not reproduce the committed file")

        shutil.copyfile(
            os.path.join(ENGINE, "web_data.json"),
            os.path.join(OUT, "scenario-real.json"),
        )
        partial = build("partial", PARTIAL_CSV)
        overpaid = build("overpaid", OVERPAID_CSV)

    # The three "older engine" shapes: still renderable, simply unable to say
    # what is owed. REQUIRED_BLOCKS in validate.ts is deliberately not extended
    # to cover them, so each of these must render with an amber banner.
    droppers = (
        ("no-payments", lambda d: d["content"].pop("payments")),
        (
            "no-above-contract",
            lambda d: d["content"]["totals"].pop("above_contract_minutes"),
        ),
        ("no-monthly", lambda d: d["content"].pop("monthly")),
    )
    for name, drop in droppers:
        d = json.loads(json.dumps(real))
        drop(d)
        with open(
            os.path.join(OUT, f"scenario-{name}.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
            f.write("\n")

    report(partial, overpaid)


def report(partial: dict, overpaid: dict) -> None:
    p = partial["content"]["payments"]
    w26 = [w for w in p["unpaid_weeks"] if w["iso_week"] == "2026-W26"]
    print("\npartial (5400 paid), against the 2026-08-10 sandbox run:")
    print(f"  paid        {p['paid_minutes']:>6}  expect   5400")
    print(f"  unpaid      {p['unpaid_minutes']:>6}  expect   8793")
    print(f"  paid_up_to  {p['paid_up_to']}  expect 2026-06-21")
    print(
        f"  W26 unpaid  {w26[0]['unpaid_minutes'] if w26 else 'NOT OWING':>6}  expect   1819"
    )
    print(f"  ledger rows {len(p['ledger']):>6}  expect      2")

    o = overpaid["content"]["payments"]
    print("\noverpaid (15000 paid against 14193 accrued):")
    print(f"  unpaid      {o['unpaid_minutes']:>6}  expect      0")
    print(f"  overpaid    {o['overpaid_minutes']:>6}  expect    807")
    print(f"  weeks owing {len(o['unpaid_weeks']):>6}  expect      0")
    print(f"  warnings    {len(o['warnings']):>6}  expect      1")


if __name__ == "__main__":
    main()
