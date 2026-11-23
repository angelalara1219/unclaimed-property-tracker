"""Unclaimed property checker.

Reads customer balances and a table of state rules, then works out for each
account: which state the balance goes to, when it's presumed abandoned, which
report it lands on, and when the due diligence notice has to go out.

Usage:
    python tracker/check.py --accounts data/sample_accounts.csv --holder-state DE --as-of 2026-11-23
"""

import argparse
import csv
import datetime as dt
from pathlib import Path

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO",
    "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA",
    "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
}

ROOT = Path(__file__).resolve().parent.parent


def load_rules(path):
    rules = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rules[(row["state"], row["asset_type"])] = row
    return rules


def add_years(d, years):
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # Feb 29 in a non-leap year
        return d.replace(year=d.year + years, day=28)


def month_day(year, md):
    m, d = (int(x) for x in md.split("-"))
    return dt.date(year, m, d)


def next_on_or_after(d, md):
    candidate = month_day(d.year, md)
    return candidate if candidate >= d else month_day(d.year + 1, md)


def next_after(d, md):
    candidate = month_day(d.year, md)
    return candidate if candidate > d else month_day(d.year + 1, md)


def reporting_state(owner_state, holder_state):
    """Texas v. New Jersey priority rules.

    1. The state of the owner's last known address.
    2. If there's no usable address, the holder's state of incorporation.
    """
    s = (owner_state or "").strip().upper()
    if s in US_STATES:
        return s, "owner's last known address"
    return holder_state, "no address on file, so holder's state of incorporation"


def needs_notice(balance, rule):
    minimum = float(rule["due_diligence_min_usd"] or 0)
    if rule["due_diligence_threshold_rule"] == "more_than":
        return balance > minimum
    return balance >= minimum


def check_account(acct, rules, holder_state, as_of):
    state, why = reporting_state(acct["owner_state"], holder_state)
    asset = acct["asset_type"]
    balance = float(acct["balance_usd"])
    result = {
        "account_id": acct["account_id"],
        "asset_type": asset,
        "balance_usd": f"{balance:,.2f}",
        "report_to": state,
        "why_this_state": why,
    }

    rule = rules.get((state, asset))
    if rule is None:
        result.update(status="OUT OF SCOPE", next_step=f"No {state} rules in the starter set yet")
        return result

    last_activity = dt.date.fromisoformat(acct["last_owner_activity"])
    start = last_activity
    if rule["dormancy_start_floor"]:
        start = max(start, dt.date.fromisoformat(rule["dormancy_start_floor"]))

    presumed = add_years(start, int(rule["dormancy_years"]))
    cutoff = next_on_or_after(presumed, rule["cutoff_month_day"])
    report_due = next_after(cutoff, rule["report_due_month_day"])

    notice_by = report_due - dt.timedelta(days=int(rule["due_diligence_latest_days"]))
    notice_from = None
    if rule["due_diligence_earliest_days"]:
        notice_from = report_due - dt.timedelta(days=int(rule["due_diligence_earliest_days"]))

    send_notice = needs_notice(balance, rule)
    certified = rule["certified_mail_over_usd"] and balance > float(rule["certified_mail_over_usd"])

    if as_of > report_due:
        status = "OVERDUE"
    elif send_notice and notice_from and notice_from <= as_of <= notice_by:
        status = "SEND NOTICE NOW"
    elif send_notice and notice_from is None and presumed <= as_of <= notice_by:
        status = "SEND NOTICE NOW"
    elif as_of > notice_by and as_of <= report_due:
        status = "REPORT DUE" if not send_notice else "NOTICE WINDOW PASSED"
    elif presumed <= add_years(as_of, 1):
        status = "APPROACHING"
    else:
        status = "ACTIVE"

    window = f"{notice_from} to {notice_by}" if notice_from else f"by {notice_by}"
    result.update(
        status=status,
        presumed_abandoned=presumed.isoformat(),
        report_due=report_due.isoformat(),
        notice_window=window if send_notice else "not required (under threshold)",
        certified_mail="yes" if certified else "no",
        delivery=rule["delivery"],
    )
    return result


def write_outputs(results, as_of, holder_state, out_dir):
    out_dir.mkdir(exist_ok=True)
    cols = ["account_id", "asset_type", "balance_usd", "report_to", "why_this_state",
            "status", "presumed_abandoned", "report_due", "notice_window",
            "certified_mail", "delivery"]
    with open(out_dir / "results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow({c: r.get(c, "") for c in cols})

    lines = [
        f"# Unclaimed property check as of {as_of}",
        "",
        f"Holder state of incorporation: {holder_state}. Sample data only.",
        "",
        "| Account | Asset | Balance | Report to | Status | Presumed abandoned | Report due | Notice window |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        lines.append(
            f"| {r['account_id']} | {r['asset_type']} | ${r['balance_usd']} | {r['report_to']} | "
            f"{r['status']} | {r.get('presumed_abandoned', '')} | {r.get('report_due', '')} | "
            f"{r.get('notice_window', r.get('next_step', ''))} |"
        )
    (out_dir / "sample_run.md").write_text("\n".join(lines) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--accounts", default=str(ROOT / "data" / "sample_accounts.csv"))
    p.add_argument("--rules", default=str(ROOT / "data" / "state_rules.csv"))
    p.add_argument("--holder-state", default="DE")
    p.add_argument("--as-of", default=dt.date.today().isoformat())
    p.add_argument("--out", default=str(ROOT / "reports"))
    args = p.parse_args()

    as_of = dt.date.fromisoformat(args.as_of)
    rules = load_rules(args.rules)
    with open(args.accounts, newline="") as f:
        results = [check_account(a, rules, args.holder_state.upper(), as_of) for a in csv.DictReader(f)]

    write_outputs(results, as_of, args.holder_state.upper(), Path(args.out))
    for r in results:
        print(f"{r['account_id']:7} {r['report_to']:3} {r['asset_type']:17} {r['status']}")


if __name__ == "__main__":
    main()
