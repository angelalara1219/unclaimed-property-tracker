import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tracker"))
import check  # noqa: E402

RULES = check.load_rules(Path(__file__).resolve().parent.parent / "data" / "state_rules.csv")
AS_OF = dt.date(2026, 11, 23)


def run(owner_state, asset, balance, last_activity):
    acct = {"account_id": "T", "owner_state": owner_state, "asset_type": asset,
            "balance_usd": str(balance), "last_owner_activity": last_activity}
    return check.check_account(acct, RULES, "DE", AS_OF)


class PriorityRules(unittest.TestCase):
    def test_owner_address_wins(self):
        self.assertEqual(run("TX", "cash", 500, "2024-01-01")["report_to"], "TX")

    def test_no_address_goes_to_state_of_incorporation(self):
        self.assertEqual(run("", "cash", 500, "2024-01-01")["report_to"], "DE")


class Dormancy(unittest.TestCase):
    def test_florida_virtual_currency_is_seven_years(self):
        self.assertEqual(run("FL", "virtual_currency", 500, "2020-02-01")["presumed_abandoned"], "2027-02-01")

    def test_new_york_virtual_currency_clock_starts_nov_22_2022(self):
        self.assertEqual(run("NY", "virtual_currency", 500, "2019-01-01")["presumed_abandoned"], "2027-11-22")


class Notices(unittest.TestCase):
    def test_texas_threshold_is_more_than_250(self):
        self.assertTrue(run("TX", "cash", 250, "2024-01-01")["notice_window"].startswith("not required"))
        self.assertFalse(run("TX", "cash", 250.01, "2024-01-01")["notice_window"].startswith("not required"))

    def test_new_york_certified_mail_over_1000(self):
        self.assertEqual(run("NY", "cash", 3100, "2023-09-15")["certified_mail"], "yes")


if __name__ == "__main__":
    unittest.main()
